/**
 * PharmAI Settings — Language selector, theme toggle, and preferences
 * Languages use Sarvam AI-supported codes.
 */

// ─── Language Constants ─────────────────────────────────────────────────────
const LANGUAGES = [
  { code: 'en-IN', label: 'English', native: 'English', flag: '🇬🇧' },
  { code: 'hi-IN', label: 'Hindi', native: 'हिन्दी', flag: '🇮🇳' },
  { code: 'bn-IN', label: 'Bengali', native: 'বাংলা', flag: '🇮🇳' },
  { code: 'ta-IN', label: 'Tamil', native: 'தமிழ்', flag: '🇮🇳' },
  { code: 'te-IN', label: 'Telugu', native: 'తెలుగు', flag: '🇮🇳' },
  { code: 'mr-IN', label: 'Marathi', native: 'मराठी', flag: '🇮🇳' },
  { code: 'gu-IN', label: 'Gujarati', native: 'ગુજરાતી', flag: '🇮🇳' },
  { code: 'kn-IN', label: 'Kannada', native: 'ಕನ್ನಡ', flag: '🇮🇳' },
  { code: 'ml-IN', label: 'Malayalam', native: 'മലയാളം', flag: '🇮🇳' },
  { code: 'pa-IN', label: 'Punjabi', native: 'ਪੰਜਾਬੀ', flag: '🇮🇳' },
  { code: 'od-IN', label: 'Odia', native: 'ଓଡ଼ିଆ', flag: '🇮🇳' },
];

// ─── State ──────────────────────────────────────────────────────────────────
let selectedLang = storageGet('pharmai_lang', 'en-IN');

// ─── Language Selection ─────────────────────────────────────────────────────

function selectLanguage(langCode) {
  selectedLang = langCode;
  storageSet('pharmai_lang', langCode);
  renderLanguageSelector();
  toast(`Language set to ${LANGUAGES.find(l => l.code === langCode)?.label || langCode}`, 'success');
}

function renderLanguageSelector() {
  const container = document.getElementById('languageGrid');
  if (!container) return;

  container.innerHTML = LANGUAGES.map(l => `
    <div class="lang-option ${l.code === selectedLang ? 'selected' : ''}" onclick="selectLanguage('${l.code}')">
      <span class="lang-flag">${l.flag}</span>
      <span class="lang-name">${l.label}</span>
      <span class="lang-native">${l.native}</span>
    </div>
  `).join('');
}

// ─── Theme Toggle ───────────────────────────────────────────────────────────
// Future: dark mode toggle. For now, only Aura teal theme.

let currentTheme = storageGet('pharmai_theme', 'light');

function toggleTheme() {
  currentTheme = currentTheme === 'light' ? 'dark' : 'light';
  storageSet('pharmai_theme', currentTheme);
  document.documentElement.setAttribute('data-theme', currentTheme);
  toast(`${currentTheme === 'dark' ? '🌙' : '☀️'} Theme switched`, 'success');
}

// ─── Settings Panel ─────────────────────────────────────────────────────────

function showSettingsPanel() {
  showToolPanel('settings');
  renderLanguageSelector();
}

// ─── Init ───────────────────────────────────────────────────────────────────

function initSettings() {
  // Apply saved theme
  document.documentElement.setAttribute('data-theme', currentTheme);

  // Render language selector
  renderLanguageSelector();

  // Theme toggle button
  document.getElementById('themeToggleBtn')?.addEventListener('click', toggleTheme);
}
