/**
 * PharmAI Search — 2-tier search with session history context
 * Tier 1: AWS RAG Knowledge Base (via N8N)
 * Tier 2: Sarvam AI fallback (sarvam-m)
 *
 * Sends conversation history for context-aware follow-up queries.
 */

// ─── Constants ──────────────────────────────────────────────────────────────
const SEARCH_DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 2;
const MAX_HISTORY_MESSAGES = 10;  // Max history entries sent to backend for context

// ─── Search Execution ───────────────────────────────────────────────────────

/**
 * Performs a context-aware search.
 * If an active session exists, conversation history is attached for follow-up context.
 *
 * @param {string} query - User's search query text
 * @returns {Promise<void>}
 */
async function performSearch(query) {
  if (!query || query.trim().length < MIN_QUERY_LENGTH) return;

  query = query.trim();

  // Ensure we have a session (create one if none active)
  if (!activeSessionId) {
    createSession();
  }

  // Add user message to session
  addMessage(activeSessionId, {
    role: 'user',
    content: query,
    timestamp: Date.now(),
  });
  renderChatView();

  // Build history array from current session for context
  const session = getSession(activeSessionId);
  const history = buildHistoryArray(session);

  // Build request payload
  const payload = {
    query: query,
    language: selectedLang || 'en-IN',
  };

  // Attach history for context-aware follow-ups (only if > 1 message)
  if (history.length > 1) {
    payload.history = history;
  }

  // Attach active space for system instruction context
  const space = getSpaceById(session?.spaceId);
  if (space && space.id !== 'default' && space.systemInstruction) {
    payload.space_context = space.systemInstruction;
  }

  // Show typing indicator
  showTypingIndicator('Searching knowledge base...');

  try {
    const res = await fetch(apiUrl('/api/search'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    removeTypingIndicator();

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    if (data.error) throw new Error(data.error);

    // Extract answer text and metadata
    const answer = data.answer || data.response || 'No result found.';
    const source = data.source || (data.tier === 1 ? 'kb' : 'sarvam');
    const citations = data.citations || [];

    // Add assistant message with response
    addMessage(activeSessionId, {
      role: 'assistant',
      content: answer,
      timestamp: Date.now(),
      source: source,
      // Structured verdict from the API. The badge must never be inferred from
      // the answer prose — see detectDrugStatus in utils.js.
      status: data.status || null,
      citations: citations,
      metadata: {
        tier: data.tier,
        model: data.model,
        latency_ms: data.latency_ms,
      },
    });

    renderChatView();
    addRecentSearch(query);

  } catch (err) {
    removeTypingIndicator();
    addMessage(activeSessionId, {
      role: 'assistant',
      content: `⚠️ Search failed: ${err.message}. Please try again.`,
      timestamp: Date.now(),
      source: 'error',
    });
    renderChatView();
    toast('Search failed', 'error');
  }
}

/**
 * Builds a conversation history array for the backend.
 * Only the last MAX_HISTORY_MESSAGES exchanges are sent.
 *
 * @param {Object} session - Session object with messages array
 * @returns {Array} History array [{role, content}, ...]
 */
function buildHistoryArray(session) {
  if (!session?.messages) return [];

  // Filter to user + assistant messages only (not system)
  const relevant = session.messages.filter(m => m.role === 'user' || m.role === 'assistant');

  // Take last N messages for context window
  return relevant.slice(-MAX_HISTORY_MESSAGES).map(m => ({
    role: m.role,
    content: m.content,
  }));
}

// ─── Recent Searches ────────────────────────────────────────────────────────
const RECENT_SEARCHES_KEY = 'pharmai_recent_searches';
const MAX_RECENT = 10;

function getRecentSearches() {
  return storageGet(RECENT_SEARCHES_KEY, []);
}

function addRecentSearch(query) {
  let recent = getRecentSearches();
  // Remove duplicate if exists
  recent = recent.filter(q => q.toLowerCase() !== query.toLowerCase());
  // Add to front
  recent.unshift(query);
  // Limit
  recent = recent.slice(0, MAX_RECENT);
  storageSet(RECENT_SEARCHES_KEY, recent);
}

function clearRecentSearches() {
  storageSet(RECENT_SEARCHES_KEY, []);
}

// ─── Search Form Handler ────────────────────────────────────────────────────

/**
 * Called by the search form submit event.
 * Reads input, clears it, triggers search.
 */
function handleSearchSubmit(e) {
  e.preventDefault();
  const input = document.getElementById('searchInput');
  const query = input.value.trim();
  if (!query) return;
  input.value = '';
  performSearch(query);
}

// ─── Template Queries (Landing Page) ────────────────────────────────────────

/**
 * When user clicks a template card on the landing page,
 * populate search and execute.
 */
function handleTemplateClick(query) {
  const input = document.getElementById('searchInput');
  if (input) input.value = query;
  performSearch(query);
}
