/**
 * PharmAI App — Main orchestrator
 *
 * Initializes all modules, sets up global event listeners,
 * and manages top-level routing between views (landing, chat, tools).
 *
 * Load order matters — this file must be loaded LAST after all modules:
 *   utils.js → notifications.js → auth.js → settings.js → spaces.js →
 *   chat.js → search.js → sidebar.js → voice.js → ocr.js →
 *   documents.js → interaction.js → export.js → app.js
 */

// ─── Global Config ──────────────────────────────────────────────────────────
const APP_VERSION = '2.0.0';

// ─── Tool Panel Management ─────────────────────────────────────────────────
// Tool panels are side features (OCR, Interaction, Documents, Settings)
// that temporarily replace the main chat view.

let activeToolPanel = null;

/**
 * Show a tool panel, hiding the chat/landing view.
 * Valid panels: 'ocr', 'interaction', 'documents', 'settings'
 */
function showToolPanel(panelName) {
  // Hide landing and chat views
  document.getElementById('landingView').style.display = 'none';
  document.getElementById('chatView').style.display = 'none';

  // Hide all tool panels
  document.querySelectorAll('.tool-panel').forEach(p => p.style.display = 'none');

  // Show requested panel
  const panel = document.getElementById(`toolPanel-${panelName}`);
  if (panel) {
    panel.style.display = '';
    activeToolPanel = panelName;

    // Panel-specific init
    if (panelName === 'documents') loadDocuments();
    if (panelName === 'settings') renderLanguageSelector();
  }

  closeSidebarMobile();
}

/**
 * Close the current tool panel and return to chat or landing view.
 */
function closeToolPanel() {
  document.querySelectorAll('.tool-panel').forEach(p => p.style.display = 'none');
  activeToolPanel = null;

  // Show appropriate view
  if (activeSessionId) {
    renderChatView();
  } else {
    showLandingView();
  }
}

// ─── Template Cards (Landing Page) ─────────────────────────────────────────

const TEMPLATE_QUERIES = [
  {
    icon: '💊',
    title: 'Drug Safety',
    query: 'Is Paracetamol safe during pregnancy?',
  },
  {
    icon: '⚠️',
    title: 'Side Effects',
    query: 'Common side effects of Metformin 500mg',
  },
  {
    icon: '🔄',
    title: 'Drug Interaction',
    query: 'Interaction between Aspirin and Warfarin',
  },
  {
    icon: '📋',
    title: 'Dosage Info',
    query: 'Recommended dosage of Amoxicillin for adults',
  },
  {
    icon: '🏥',
    title: 'CDSCO Status',
    query: 'Is Nimesulide banned in India?',
  },
  {
    icon: '🧬',
    title: 'Drug Composition',
    query: 'Active ingredients in Crocin Advance',
  },
];

function renderTemplateCards() {
  const container = document.getElementById('templateGrid');
  if (!container) return;

  container.innerHTML = TEMPLATE_QUERIES.map(t => `
    <div class="template-card" onclick="handleTemplateClick('${escapeHtml(t.query).replace(/'/g, "\\'")}')">
      <div class="template-icon">${t.icon}</div>
      <div class="template-title">${t.title}</div>
      <div class="template-query">${escapeHtml(t.query)}</div>
    </div>
  `).join('');
}

// ─── Search Bar Setup ───────────────────────────────────────────────────────

function setupSearchBar() {
  const form = document.getElementById('searchForm');
  form?.addEventListener('submit', handleSearchSubmit);

  const input = document.getElementById('searchInput');
  if (input) {
    // Auto-resize textarea on input
    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });

    // Ctrl+Enter or Enter (without Shift) to submit
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        form?.requestSubmit();
      }
    });
  }
}

// ─── Sidebar Tool Buttons Setup ─────────────────────────────────────────────

function setupSidebarToolButtons() {
  document.getElementById('toolOcr')?.addEventListener('click', () => showToolPanel('ocr'));
  document.getElementById('toolInteraction')?.addEventListener('click', () => showToolPanel('interaction'));
  document.getElementById('toolDocuments')?.addEventListener('click', () => showToolPanel('documents'));
  document.getElementById('toolSettings')?.addEventListener('click', () => showToolPanel('settings'));

  // Close tool panel buttons
  document.querySelectorAll('.tool-panel-close').forEach(btn => {
    btn.addEventListener('click', closeToolPanel);
  });
}

// ─── Export Buttons Setup ───────────────────────────────────────────────────

function setupExportButtons() {
  document.getElementById('btnCopyChat')?.addEventListener('click', copyFullChat);
  document.getElementById('btnExportPdf')?.addEventListener('click', exportChatPDF);
  document.getElementById('btnShareChat')?.addEventListener('click', shareChat);
}

// ─── Scroll-to-Bottom FAB ───────────────────────────────────────────────────

function setupScrollFab() {
  const fab = document.getElementById('scrollFab');
  if (!fab) return;

  // Show/hide based on scroll position
  const chatContainer = document.getElementById('chatMessages');
  if (chatContainer) {
    const observer = new IntersectionObserver((entries) => {
      // When the last message is NOT visible, show the FAB
      fab.classList.toggle('visible', !entries[0]?.isIntersecting);
    }, { threshold: 0.1 });

    // Observe the last child (re-observe when messages change)
    const observeLast = () => {
      if (chatContainer.lastElementChild) {
        observer.disconnect();
        observer.observe(chatContainer.lastElementChild);
      }
    };
    // Use MutationObserver to re-observe when messages are added
    new MutationObserver(observeLast).observe(chatContainer, { childList: true });
    observeLast();
  }

  fab.addEventListener('click', () => scrollToBottom(true));
}

// ─── Disclaimer ─────────────────────────────────────────────────────────────

function showDisclaimer() {
  const key = 'pharmai_disclaimer_accepted';
  if (storageGet(key, false)) return;

  const disclaimer = document.getElementById('disclaimerBanner');
  if (!disclaimer) return;

  disclaimer.style.display = '';
  document.getElementById('acceptDisclaimer')?.addEventListener('click', () => {
    storageSet(key, true);
    disclaimer.style.display = 'none';
  });
}

// ─── Main Initialization ────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  console.log(`⚕️ PharmAI v${APP_VERSION} initializing...`);

  // Initialize all modules (order matters for dependencies)
  initSettings();       // Language + theme (needed by other modules)
  initSpaces();         // Spaces (needed by Sessions)
  initSidebar();        // Sidebar + session list + loads sessions
  setupSearchBar();     // Search form
  setupSidebarToolButtons();
  setupExportButtons();
  initVoice();          // STT/TTS
  initOcr();            // Prescription scanner
  initDocuments();      // KB document management
  initInteraction();    // Drug interaction checker
  setupScrollFab();     // Scroll-to-bottom button

  // Render landing view templates
  renderTemplateCards();
  showLandingView();
  showDisclaimer();

  // Initialize auth (async - might need network)
  const auth = new DescopeAuth();
  auth.init(); // Single init call (constructor no longer calls init())

  // Update space indicator on search bar
  updateSpaceIndicator();

  console.log(`⚕️ PharmAI v${APP_VERSION} ready`);
});
