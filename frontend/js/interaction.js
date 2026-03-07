/**
 * PharmAI Drug Interaction Checker
 * Lets users check interactions between two drugs using Sarvam AI.
 */

// ─── Interaction Check ──────────────────────────────────────────────────────

/**
 * Check interaction between two drugs.
 * Sends both drug names to the search endpoint with a
 * structured interaction query.
 *
 * @param {string} drug1 - First drug name
 * @param {string} drug2 - Second drug name
 */
async function checkInteraction(drug1, drug2) {
  if (!drug1 || !drug2) {
    toast('Enter both drug names', 'error');
    return;
  }

  const query = `Drug-Drug Interaction Analysis: ${drug1.trim()} and ${drug2.trim()}. Provide: severity, mechanism of interaction, clinical significance, management recommendations, alternative drugs if needed.`;

  // Use the main search flow which creates a session and renders results
  performSearch(query);
}

// ─── Interaction Panel ──────────────────────────────────────────────────────

function showInteractionPanel() {
  showToolPanel('interaction');
}

function handleInteractionSubmit(e) {
  e?.preventDefault();
  const drug1 = document.getElementById('interDrug1')?.value;
  const drug2 = document.getElementById('interDrug2')?.value;
  checkInteraction(drug1, drug2);
}

// ─── Init ───────────────────────────────────────────────────────────────────

function initInteraction() {
  const form = document.getElementById('interactionForm');
  form?.addEventListener('submit', handleInteractionSubmit);
}
