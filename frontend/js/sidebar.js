/**
 * PharmAI Sidebar — Mobile/desktop sidebar toggle, session list rendering
 * Perplexity-style sliding sidebar with conversation history
 */

// ─── State ──────────────────────────────────────────────────────────────────
let sidebarOpen = false;

// ─── Sidebar Toggle ─────────────────────────────────────────────────────────

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (!sidebar) return;

  sidebarOpen = !sidebarOpen;
  sidebar.classList.toggle('open', sidebarOpen);
  backdrop?.classList.toggle('active', sidebarOpen);
  document.body.classList.toggle('sidebar-open', sidebarOpen);
}

function openSidebar() {
  if (!sidebarOpen) toggleSidebar();
}

function closeSidebar() {
  if (sidebarOpen) toggleSidebar();
}

/**
 * On mobile, close sidebar after selecting a conversation.
 * On desktop (>1024px), sidebar stays open.
 */
function closeSidebarMobile() {
  if (window.innerWidth < 1024 && sidebarOpen) {
    closeSidebar();
  }
}

// ─── New Chat ───────────────────────────────────────────────────────────────

/**
 * Creates a new empty session and shows the landing view.
 * Called when user clicks "+ New Chat" in sidebar.
 */
function handleNewChat() {
  createSession();
  showLandingView();
  closeSidebarMobile();

  // Focus the search input for immediate typing
  setTimeout(() => {
    document.getElementById('searchInput')?.focus();
  }, 100);
}

// ─── Tools Panel (Sidebar Footer) ──────────────────────────────────────────

/**
 * Set up event listeners for sidebar footer tool buttons.
 * These open tool panels (OCR, Drug Interaction, Documents, KB Upload, Settings).
 */
function setupSidebarTools() {
  // Tool buttons in sidebar footer are wired up in app.js init
  // They trigger showToolPanel('name') which drives the main content area
}

// ─── Sidebar Initialization ────────────────────────────────────────────────

function initSidebar() {
  // Hamburger button
  const hamburgerBtn = document.getElementById('hamburgerBtn');
  hamburgerBtn?.addEventListener('click', toggleSidebar);

  // Hover to Peek Logic
  let hoverOpenTimeout;
  let hoverCloseTimeout;
  const sidebar = document.getElementById('sidebar');

  hamburgerBtn?.addEventListener('mouseenter', () => {
    clearTimeout(hoverCloseTimeout);
    hoverOpenTimeout = setTimeout(() => {
      openSidebar();
    }, 200);
  });

  hamburgerBtn?.addEventListener('mouseleave', () => {
    clearTimeout(hoverOpenTimeout);
  });

  sidebar?.addEventListener('mouseenter', () => {
    clearTimeout(hoverCloseTimeout);
  });

  sidebar?.addEventListener('mouseleave', () => {
    hoverCloseTimeout = setTimeout(() => {
      closeSidebar();
    }, 500);
  });

  // Backdrop click to close
  const backdrop = document.getElementById('sidebarBackdrop');
  backdrop?.addEventListener('click', closeSidebar);

  // New Chat button
  const newChatBtn = document.getElementById('newChatBtn');
  newChatBtn?.addEventListener('click', handleNewChat);

  // Load and render sessions on init
  loadSessions();
  renderSessionList();

  // NOTE: Sidebar starts CLOSED on all screen sizes to prevent
  // blurred backdrop on first load. User can toggle with hamburger.
  // Previously auto-opened on desktop (>=1024px) which caused blur issues.
}
