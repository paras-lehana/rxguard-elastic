/**
 * PharmAI Utils — Shared utility functions
 * Time formatting, API helpers, markdown rendering, localStorage wrappers
 */

// ─── API URL Builder ────────────────────────────────────────────────────────
// Builds API URLs relative to the current page path (Traefik strips /pharmai prefix)
function apiUrl(path) {
  const base = window.location.pathname.replace(/\/+$/, '');
  return base + path;
}

// ─── Markdown Rendering ─────────────────────────────────────────────────────
// Uses Marked.js if available, falls back to basic regex formatting
function renderMd(text) {
  if (typeof marked !== 'undefined') {
    return marked.parse(text || '');
  }
  return (text || '')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

// ─── Time Helpers ───────────────────────────────────────────────────────────
// Returns a human-readable relative time string (e.g., "5m ago", "2h ago")
function timeAgo(ts) {
  const diff = Date.now() - ts;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
  if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
  return Math.floor(diff / 86400000) + 'd ago';
}

// Categorizes a timestamp into display groups for the sidebar session list
function getDateGroup(ts) {
  const now = new Date();
  const date = new Date(ts);
  const diffDays = Math.floor((now - date) / 86400000);

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return 'Previous 7 Days';
  return 'Older';
}

// ─── File Size Formatter ────────────────────────────────────────────────────
function formatBytes(b) {
  if (b === 0) return '0 B';
  const k = 1024, s = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(b) / Math.log(k));
  return parseFloat((b / Math.pow(k, i)).toFixed(1)) + ' ' + s[i];
}

// ─── UUID-like ID Generator ─────────────────────────────────────────────────
// Uses crypto.randomUUID if available, else fallback to timestamp + random
function generateId(prefix = '') {
  const id = typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID().slice(0, 8)
    : Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  return prefix ? `${prefix}_${id}` : id;
}

// ─── LocalStorage Helpers ───────────────────────────────────────────────────
// Safe JSON read/write wrappers that handle quota errors and parse failures
function storageGet(key, defaultValue = null) {
  try {
    const val = localStorage.getItem(key);
    return val ? JSON.parse(val) : defaultValue;
  } catch {
    return defaultValue;
  }
}

function storageSet(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (e) {
    // localStorage full — try clearing old data
    console.warn('localStorage quota exceeded:', e);
    return false;
  }
}

// ─── HTML Sanitizer ─────────────────────────────────────────────────────────
// Basic XSS prevention for user-generated content inserted into DOM
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ─── Debounce ───────────────────────────────────────────────────────────────
function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// ─── Detect Drug Status from Text ───────────────────────────────────────────
// Scans AI response text to determine the drug's regulatory status for badge display
// LEGACY FALLBACK ONLY. Prefer the `status` field the API now returns.
//
// Substring-matching prose for "banned" is unsafe: an answer saying "there is
// no information regarding a ban" contains the word and used to be badged
// 🚫 BANNED, contradicting its own body text. Negation and hedging phrases are
// now checked first, and an ambiguous answer returns null so no badge renders —
// showing nothing is always safer than showing the wrong verdict.
function detectDrugStatus(text) {
  if (!text) return null;
  const lower = text.toLowerCase();

  const hedges = [
    'no information', 'not explicitly', 'does not state', 'do not state',
    'does not answer', 'not covered', 'missing from', 'not found',
    'insufficient', 'cannot determine', 'unable to determine',
    'no evidence', 'not mention', 'no mention', 'not specify',
  ];
  if (hedges.some((h) => lower.includes(h))) return null;

  if (lower.includes('banned') || lower.includes('prohibited')) return 'banned';
  if (lower.includes('restricted') || lower.includes('controlled')) return 'restricted';
  if (lower.includes('approved') || lower.includes('allowed') || lower.includes('permitted')) return 'approved';
  return null;
}
