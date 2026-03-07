/**
 * PharmAI Notifications — Toast notification system
 * Supports: success, error, info, warning
 * Auto-dismisses after timeout. Stacks multiple toasts.
 */

// ─── Constants ──────────────────────────────────────────────────────────────
const TOAST_TIMEOUT_MS = 3500;
const MAX_VISIBLE_TOASTS = 4;

// ─── Toast Display ──────────────────────────────────────────────────────────

/**
 * Show a toast notification.
 *
 * @param {string} message - Text to display
 * @param {string} type - 'success' | 'error' | 'info' | 'warning'
 * @param {number} duration - Auto-dismiss duration in ms (0 = manual close)
 */
function toast(message, type = 'info', duration = TOAST_TIMEOUT_MS) {
  const container = getToastContainer();

  // Limit visible toasts
  while (container.children.length >= MAX_VISIBLE_TOASTS) {
    container.removeChild(container.firstChild);
  }

  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };

  const toastEl = document.createElement('div');
  toastEl.className = `toast toast-${type}`;
  toastEl.innerHTML = `
    <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
    <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
  `;

  container.appendChild(toastEl);

  // Trigger animation
  requestAnimationFrame(() => toastEl.classList.add('visible'));

  // Auto-dismiss
  if (duration > 0) {
    setTimeout(() => {
      toastEl.classList.remove('visible');
      setTimeout(() => toastEl.remove(), 300);
    }, duration);
  }
}

/**
 * Get or create the toast container element.
 * Positioned at top-right of viewport.
 */
function getToastContainer() {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  return container;
}
