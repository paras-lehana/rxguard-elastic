/**
 * PharmAI Spaces — Persona/context system (like Perplexity Spaces)
 * Each space has a name, icon, system instruction, and optional color.
 * Sessions are tagged to spaces for filtered views.
 */

// ─── Constants ──────────────────────────────────────────────────────────────
const STORAGE_KEY_SPACES = 'pharmai_spaces';
const STORAGE_KEY_ACTIVE_SPACE = 'pharmai_active_space';

// ─── Default Spaces ─────────────────────────────────────────────────────────
const DEFAULT_SPACES = [
  {
    id: 'default',
    name: 'General',
    icon: '🔍',
    color: '#0D9488',
    systemInstruction: '',
    isDefault: true,
  },
  {
    id: 'doctor',
    name: 'Doctor',
    icon: '🩺',
    color: '#2563EB',
    systemInstruction: 'You are assisting a medical doctor. Provide detailed clinical information, drug-drug interactions, contraindications, dosage adjustments for comorbidities, and evidence-based recommendations. Use medical terminology freely.',
    isDefault: true,
  },
  {
    id: 'pharmacist',
    name: 'Pharmacist',
    icon: '💊',
    color: '#7C3AED',
    systemInstruction: 'You are assisting a pharmacist. Focus on formulation details, storage conditions, bioavailability, dispensing guidelines, Schedule H/H1/X classifications, CDSCO compliance, and patient counseling points.',
    isDefault: true,
  },
  {
    id: 'patient',
    name: 'Patient',
    icon: '👤',
    color: '#059669',
    systemInstruction: 'You are assisting a patient in India. Explain in simple, non-technical language. Include: what the medicine does, common side effects, when to take it, food interactions, and when to seek medical help. Avoid jargon.',
    isDefault: true,
  },
  {
    id: 'researcher',
    name: 'Researcher',
    icon: '🔬',
    color: '#DC2626',
    systemInstruction: 'You are assisting a pharmaceutical researcher. Provide detailed mechanism of action, pharmacokinetics/pharmacodynamics data, clinical trial references, molecular structure details, and regulatory pathway information.',
    isDefault: true,
  },
];

// ─── State ──────────────────────────────────────────────────────────────────
let spaces = [];
let activeSpaceId = 'default';

// ─── Load & Save ────────────────────────────────────────────────────────────

function loadSpaces() {
  const stored = storageGet(STORAGE_KEY_SPACES, null);

  if (!stored || !Array.isArray(stored)) {
    // First time — initialize with defaults
    spaces = JSON.parse(JSON.stringify(DEFAULT_SPACES));
    saveSpaces();
  } else {
    spaces = stored;
    // Ensure all default spaces still exist (user may have cleared storage)
    for (const d of DEFAULT_SPACES) {
      if (!spaces.find(s => s.id === d.id)) {
        spaces.push(d);
      }
    }
  }

  activeSpaceId = storageGet(STORAGE_KEY_ACTIVE_SPACE, 'default');
}

function saveSpaces() {
  storageSet(STORAGE_KEY_SPACES, spaces);
}

function saveActiveSpace() {
  storageSet(STORAGE_KEY_ACTIVE_SPACE, activeSpaceId);
}

// ─── Space CRUD ─────────────────────────────────────────────────────────────

function createSpace(name, icon, systemInstruction, color) {
  const space = {
    id: generateId('space'),
    name: name.trim(),
    icon: icon || '📁',
    color: color || '#6B7280',
    systemInstruction: systemInstruction || '',
    isDefault: false,
  };
  spaces.push(space);
  saveSpaces();
  renderSpaceSelector();
  return space;
}

function updateSpace(spaceId, updates) {
  const space = getSpaceById(spaceId);
  if (!space || space.isDefault) return; // Cannot edit default spaces
  Object.assign(space, updates);
  saveSpaces();
  renderSpaceSelector();
}

function deleteSpace(spaceId) {
  const space = getSpaceById(spaceId);
  if (!space || space.isDefault) return; // Cannot delete default spaces

  spaces = spaces.filter(s => s.id !== spaceId);
  saveSpaces();

  // If deleted the active space, fallback to default
  if (activeSpaceId === spaceId) {
    setActiveSpace('default');
  }
  renderSpaceSelector();
}

function getSpaceById(spaceId) {
  return spaces.find(s => s.id === spaceId) || null;
}

function getActiveSpaceId() {
  return activeSpaceId || 'default';
}

function setActiveSpace(spaceId) {
  activeSpaceId = spaceId;
  saveActiveSpace();
  renderSpaceSelector();
  renderSessionList();
  updateSpacePromptEditor();  // Show/hide custom prompt textarea
}

// ─── Space Selector UI ─────────────────────────────────────────────────────

function renderSpaceSelector() {
  const container = document.getElementById('spaceSelector');
  if (!container) return;

  const active = getSpaceById(activeSpaceId) || spaces[0];

  // Render the current space button
  const btn = container.querySelector('.space-current');
  if (btn) {
    btn.innerHTML = `${active.icon} ${active.name} <span class="dropdown-arrow">▾</span>`;
  }

  // Render dropdown items
  const dropdown = container.querySelector('.space-dropdown');
  if (dropdown) {
    dropdown.innerHTML = spaces.map(s => `
      <div class="space-option ${s.id === activeSpaceId ? 'active' : ''}" onclick="setActiveSpace('${s.id}')">
        <span class="space-icon">${s.icon}</span>
        <span class="space-name">${escapeHtml(s.name)}</span>
        ${!s.isDefault ? `<button class="space-delete" onclick="event.stopPropagation(); deleteSpace('${s.id}')">✕</button>` : ''}
      </div>
    `).join('') + `
      <div class="space-option create-space" onclick="showCreateSpaceModal()">
        <span class="space-icon">➕</span>
        <span class="space-name">Create Space</span>
      </div>
    `;
  }
}

function toggleSpaceDropdown() {
  const dropdown = document.querySelector('.space-dropdown');
  if (!dropdown) return;
  dropdown.classList.toggle('visible');
}

// ─── Create Space Modal ─────────────────────────────────────────────────────

function showCreateSpaceModal() {
  const modal = document.getElementById('createSpaceModal');
  if (!modal) return;

  // Reset form
  document.getElementById('spaceNameInput').value = '';
  document.getElementById('spaceInstructionInput').value = '';
  document.getElementById('spaceIconInput').value = '📁';

  modal.classList.add('active');
  document.getElementById('spaceNameInput')?.focus();
}

function hideCreateSpaceModal() {
  document.getElementById('createSpaceModal')?.classList.remove('active');
}

function handleCreateSpace(e) {
  e?.preventDefault();
  const name = document.getElementById('spaceNameInput')?.value;
  const instruction = document.getElementById('spaceInstructionInput')?.value;
  const icon = document.getElementById('spaceIconInput')?.value || '📁';

  if (!name || !name.trim()) {
    toast('Space name is required', 'error');
    return;
  }

  const space = createSpace(name, icon, instruction);
  setActiveSpace(space.id);
  hideCreateSpaceModal();
  toast(`Space "${name}" created!`, 'success');
}

// ─── Space Search Bar Badge ─────────────────────────────────────────────────

/**
 * Updates the badge above the search input showing the active space.
 * Shows nothing for "General" space.
 */
function updateSpaceIndicator() {
  const indicator = document.getElementById('spaceIndicator');
  if (!indicator) return;

  const space = getSpaceById(activeSpaceId);
  if (!space || space.id === 'default') {
    indicator.style.display = 'none';
  } else {
    indicator.style.display = '';
    indicator.innerHTML = `${space.icon} ${space.name}`;
    indicator.style.background = space.color + '22';
    indicator.style.color = space.color;
  }
}

// ─── Custom System Prompt Editor ────────────────────────────────────────────

/**
 * Show/hide the inline system prompt textarea based on active space.
 * Default space hides the editor. Non-default spaces show it with
 * the space's current systemInstruction pre-filled.
 */
function updateSpacePromptEditor() {
  const editor = document.getElementById('spacePromptEditor');
  const textarea = document.getElementById('spacePromptTextarea');
  if (!editor || !textarea) return;

  const space = getSpaceById(activeSpaceId);
  if (!space || space.id === 'default') {
    editor.style.display = 'none';
    return;
  }

  editor.style.display = '';
  textarea.value = space.systemInstruction || '';
}

/**
 * Handle changes to the custom system prompt textarea.
 * Auto-saves the instruction to the active space on blur.
 */
function handleSpacePromptChange() {
  const textarea = document.getElementById('spacePromptTextarea');
  if (!textarea) return;

  const space = getSpaceById(activeSpaceId);
  if (!space || space.isDefault) return;  // Cannot edit default spaces' prompts

  space.systemInstruction = textarea.value;
  saveSpaces();
}

// ─── Init ───────────────────────────────────────────────────────────────────

function initSpaces() {
  loadSpaces();
  renderSpaceSelector();
  updateSpaceIndicator();

  // Space selector toggle
  const currentBtn = document.querySelector('.space-current');
  currentBtn?.addEventListener('click', toggleSpaceDropdown);

  // Close dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.space-selector')) {
      document.querySelector('.space-dropdown')?.classList.remove('visible');
    }
  });

  // Create space form
  document.getElementById('createSpaceForm')?.addEventListener('submit', handleCreateSpace);
  document.getElementById('cancelCreateSpace')?.addEventListener('click', hideCreateSpaceModal);

  // Custom system prompt editor — auto-save on blur
  const promptTextarea = document.getElementById('spacePromptTextarea');
  if (promptTextarea) {
    promptTextarea.addEventListener('blur', handleSpacePromptChange);
    promptTextarea.addEventListener('change', handleSpacePromptChange);
  }

  // Initialize prompt editor visibility
  updateSpacePromptEditor();
}
