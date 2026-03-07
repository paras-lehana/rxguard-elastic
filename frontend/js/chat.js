/**
 * PharmAI Chat — Session-based conversation management
 * Handles message rendering, session CRUD, scroll management
 */

// ─── Constants ──────────────────────────────────────────────────────────────
const MAX_SESSIONS = 50;    // Maximum sessions in localStorage before eviction
const STORAGE_KEY_SESSIONS = 'pharmai_sessions';
const STORAGE_KEY_ACTIVE = 'pharmai_active_session';

// ─── State ──────────────────────────────────────────────────────────────────
let sessions = [];       // Array of session objects
let activeSessionId = null;  // Currently displayed session ID

// ─── Session Schema ─────────────────────────────────────────────────────────
// {
//   id: 'session_xxxxxxxx',
//   title: 'First query text...',
//   spaceId: 'default',
//   messages: [
//     { role: 'user'|'assistant'|'system', content: '...', timestamp: 123,
//       source: 'kb'|'sarvam'|null, citations: [], metadata: {} }
//   ],
//   createdAt: 123,
//   updatedAt: 123,
// }

// ─── Load & Save ────────────────────────────────────────────────────────────
function loadSessions() {
  sessions = storageGet(STORAGE_KEY_SESSIONS, []);
  activeSessionId = storageGet(STORAGE_KEY_ACTIVE, null);

  // Validate active session still exists
  if (activeSessionId && !sessions.find(s => s.id === activeSessionId)) {
    activeSessionId = null;
    storageSet(STORAGE_KEY_ACTIVE, null);
  }
}

function saveSessions() {
  // Enforce session limit — evict oldest when exceeding max
  if (sessions.length > MAX_SESSIONS) {
    sessions.sort((a, b) => b.updatedAt - a.updatedAt);
    sessions = sessions.slice(0, MAX_SESSIONS);
  }
  storageSet(STORAGE_KEY_SESSIONS, sessions);
}

function saveActiveSession() {
  storageSet(STORAGE_KEY_ACTIVE, activeSessionId);
}

// ─── Session CRUD ───────────────────────────────────────────────────────────
function createSession(spaceId = null) {
  const session = {
    id: generateId('session'),
    title: '',
    spaceId: spaceId || getActiveSpaceId(),
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
  sessions.unshift(session);
  saveSessions();
  setActiveSession(session.id);

  // Add system message for space context
  const space = getSpaceById(session.spaceId);
  if (space && space.id !== 'default') {
    addMessage(session.id, {
      role: 'system',
      content: `Session started in ${space.icon} ${space.name}`,
      timestamp: Date.now(),
    });
  }

  return session;
}

function getSession(sessionId) {
  return sessions.find(s => s.id === sessionId) || null;
}

function setActiveSession(sessionId) {
  activeSessionId = sessionId;
  saveActiveSession();
  renderSessionList();
  renderChatView();
}

function deleteSession(sessionId) {
  sessions = sessions.filter(s => s.id !== sessionId);
  saveSessions();

  // If we deleted the active session, clear the view
  if (activeSessionId === sessionId) {
    activeSessionId = null;
    saveActiveSession();
    showLandingView();
  }
  renderSessionList();
}

function renameSession(sessionId, title) {
  const session = getSession(sessionId);
  if (session) {
    session.title = title;
    session.updatedAt = Date.now();
    saveSessions();
    renderSessionList();
  }
}

function addMessage(sessionId, message) {
  const session = getSession(sessionId);
  if (!session) return;

  session.messages.push(message);
  session.updatedAt = Date.now();

  // Auto-set title from first user message
  if (!session.title && message.role === 'user') {
    session.title = message.content.slice(0, 60);
  }

  saveSessions();
}

function getAllSessions() {
  return [...sessions].sort((a, b) => b.updatedAt - a.updatedAt);
}

// ─── Chat View Rendering ────────────────────────────────────────────────────
function showLandingView() {
  document.getElementById('landingView').style.display = '';
  document.getElementById('chatView').style.display = 'none';
}

function showChatView() {
  document.getElementById('landingView').style.display = 'none';
  document.getElementById('chatView').style.display = '';
}

function renderChatView() {
  const session = getSession(activeSessionId);
  if (!session) {
    showLandingView();
    return;
  }

  showChatView();
  const container = document.getElementById('chatMessages');
  container.innerHTML = '';

  for (const msg of session.messages) {
    container.appendChild(createMessageElement(msg));
  }

  scrollToBottom();
}

function createMessageElement(msg) {
  const wrapper = document.createElement('div');
  wrapper.className = `chat-msg ${msg.role}`;

  if (msg.role === 'user') {
    wrapper.innerHTML = `<div class="msg-bubble">${escapeHtml(msg.content)}</div>`;
  } else if (msg.role === 'assistant') {
    const status = detectDrugStatus(msg.content);
    const statusBadge = status ? `<span class="status-badge status-${status}">${getStatusEmoji(status)} ${status.toUpperCase()}</span>` : '';
    const sourceBadge = msg.source ? `<span class="source-badge">${msg.source === 'kb' ? '📚 AWS KB' : '🤖 Sarvam AI'}</span>` : '';

    let citationsHtml = '';
    if (msg.citations && msg.citations.length > 0) {
      citationsHtml = `
        <div class="msg-citations">
          <div class="citation-label">Sources</div>
          ${msg.citations.map((c, i) => `
            <div class="citation-item">
              <span class="citation-num">${i + 1}</span>
              <span class="citation-text"><span class="citation-doc">${escapeHtml(c.docName || 'Document')}</span>${c.excerpt ? ': ' + escapeHtml(c.excerpt.slice(0, 100)) + '...' : ''}</span>
            </div>
          `).join('')}
        </div>
      `;
    }

    wrapper.innerHTML = `
      <div class="msg-avatar">⚕</div>
      <div class="msg-bubble">
        <div class="msg-header">
          ${statusBadge}
          ${sourceBadge}
        </div>
        <div class="msg-content">${renderMd(msg.content)}</div>
        ${citationsHtml}
        <div class="msg-actions">
          <button class="msg-action-btn" onclick="copyMessageText(this)" data-text="${escapeHtml(msg.content)}">📋 Copy</button>
          <button class="msg-action-btn" onclick="readMessageAloud(this)" data-text="${escapeHtml(msg.content)}">🔊 Read</button>
          <button class="msg-action-btn" onclick="translateMessage(this)" data-text="${escapeHtml(msg.content)}">🌐 Translate</button>
        </div>
      </div>
    `;
  } else if (msg.role === 'system') {
    wrapper.innerHTML = `<div class="msg-bubble">${escapeHtml(msg.content)}</div>`;
  }

  return wrapper;
}

function getStatusEmoji(status) {
  const map = { banned: '🚫', approved: '✅', restricted: '⚠️', controlled: '🔒' };
  return map[status] || '';
}

// ─── Typing Indicator ───────────────────────────────────────────────────────
function showTypingIndicator(text = 'Searching...') {
  removeTypingIndicator();
  const container = document.getElementById('chatMessages');
  const indicator = document.createElement('div');
  indicator.id = 'typingIndicator';
  indicator.className = 'chat-msg assistant';
  indicator.innerHTML = `
    <div class="msg-avatar">⚕</div>
    <div class="typing-indicator">
      <div class="typing-dots"><span></span><span></span><span></span></div>
      <span class="typing-text">${escapeHtml(text)}</span>
    </div>
  `;
  container.appendChild(indicator);
  scrollToBottom();
}

function removeTypingIndicator() {
  document.getElementById('typingIndicator')?.remove();
}

// ─── Scroll Management ─────────────────────────────────────────────────────
function scrollToBottom(smooth = true) {
  const container = document.getElementById('chatMessages');
  if (!container) return;
  // Use a small delay to ensure DOM is updated
  requestAnimationFrame(() => {
    container.scrollIntoView({ behavior: smooth ? 'smooth' : 'instant', block: 'end' });
  });
}

// ─── Session List Rendering (Sidebar) ───────────────────────────────────────
function renderSessionList() {
  const container = document.getElementById('sessionList');
  if (!container) return;

  const sorted = getAllSessions();

  if (sorted.length === 0) {
    container.innerHTML = `<div style="padding:1rem;font-size:0.78rem;color:rgba(255,255,255,0.3);text-align:center;">No conversations yet</div>`;
    return;
  }

  // Group by date
  const groups = {};
  for (const s of sorted) {
    const group = getDateGroup(s.updatedAt);
    if (!groups[group]) groups[group] = [];
    groups[group].push(s);
  }

  let html = '';
  for (const [group, items] of Object.entries(groups)) {
    html += `<div class="session-group-label">${group}</div>`;
    for (const s of items) {
      const title = s.title || 'Untitled chat';
      const isActive = s.id === activeSessionId;
      html += `
        <div class="session-item ${isActive ? 'active' : ''}" data-session-id="${s.id}" onclick="setActiveSession('${s.id}'); closeSidebarMobile();">
          <span class="session-title" title="${escapeHtml(title)}">${escapeHtml(title)}</span>
          <button class="session-delete" onclick="event.stopPropagation(); deleteSession('${s.id}')" title="Delete">✕</button>
        </div>
      `;
    }
  }

  container.innerHTML = html;
}

// ─── Message Action Handlers ────────────────────────────────────────────────
function copyMessageText(btn) {
  const text = btn.dataset.text;
  navigator.clipboard.writeText(text).then(() => toast('Copied!', 'success'));
}

async function readMessageAloud(btn) {
  const text = btn.dataset.text;
  if (!text) return;

  // Strip markdown for TTS, cap at 500 chars
  const plain = text.replace(/[#*_`\[\]()]/g, '').replace(/\n+/g, ' ').slice(0, 500);

  // Delegate to playTTS (voice.js) which manages audio state properly
  if (typeof playTTS === 'function') {
    playTTS(plain, btn);
  } else {
    // Fallback: direct call if voice.js not loaded
    btn.disabled = true;
    try {
      const res = await fetch(apiUrl('/api/tts'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: plain, language: selectedLang }),
      });
      const data = await res.json();
      if (data.audio) {
        const audio = new Audio('data:audio/wav;base64,' + data.audio);
        audio.play();
      } else {
        toast('TTS failed', 'error');
      }
    } catch (e) {
      toast('TTS error', 'error');
    }
    btn.disabled = false;
  }
}

async function translateMessage(btn) {
  const text = btn.dataset.text;
  if (!text || !selectedLang || selectedLang === 'en-IN') {
    toast('Select a language in Settings', 'info');
    return;
  }

  btn.disabled = true;
  btn.classList.add('loading');

  const plain = text.replace(/[#*_`\[\]()]/g, '').replace(/\n+/g, '\n');

  try {
    const res = await fetch(apiUrl('/api/translate'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: plain, target: selectedLang, source: 'en-IN' }),
    });
    const data = await res.json();
    if (data.translated_text) {
      // Show translated text in a new system message
      const session = getSession(activeSessionId);
      if (session) {
        addMessage(activeSessionId, {
          role: 'system',
          content: `🌐 Translated to ${LANGUAGES.find(l => l.code === selectedLang)?.label || selectedLang}`,
          timestamp: Date.now(),
        });
        addMessage(activeSessionId, {
          role: 'assistant',
          content: data.translated_text,
          timestamp: Date.now(),
          source: 'translate',
        });
        renderChatView();
      }
    } else {
      toast('Translation failed', 'error');
    }
  } catch (e) {
    toast('Translation error', 'error');
  }

  btn.disabled = false;
  btn.classList.remove('loading');
}
