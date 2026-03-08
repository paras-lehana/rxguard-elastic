/**
 * PharmAI OCR — Prescription scanning and medicine extraction
 *
 * Flow:
 * 1. User uploads prescription image (file input, camera, or drag-drop)
 * 2. Image sent to Sarvam OCR (parse/document) → raw text
 * 3. Raw text sent to Sarvam LLM (sarvam-m) for medicine extraction
 * 4. Extracted medicines displayed as interactive checklist
 * 5. User can search individual medicines or batch-search all
 */

// ─── State ──────────────────────────────────────────────────────────────────
let ocrResult = null;        // { text, medicines: [{name, dosage, frequency, checked}] }
let ocrImagePreview = null;  // Data URL of uploaded image

// ─── OCR Panel UI ───────────────────────────────────────────────────────────

function showOcrPanel() {
  showToolPanel('ocr');
}

/**
 * Handle file selection for OCR scanning.
 * Supports: file input, camera capture, drag-and-drop.
 *
 * @param {File} file - Image file to process
 */
async function handleOcrFileSelect(file) {
  if (!file) return;

  // Validate file type
  if (!file.type.startsWith('image/')) {
    toast('Please upload an image file', 'error');
    return;
  }

  // Validate file size (max 10MB)
  if (file.size > 10 * 1024 * 1024) {
    toast('Image too large. Max 10MB.', 'error');
    return;
  }

  // Show preview
  const reader = new FileReader();
  reader.onload = (e) => {
    ocrImagePreview = e.target.result;
    renderOcrPreview();
  };
  reader.readAsDataURL(file);

  // Process OCR
  await processOcrImage(file);
}

function renderOcrPreview() {
  const preview = document.getElementById('ocrPreview');
  if (!preview || !ocrImagePreview) return;

  preview.innerHTML = `
    <img src="${ocrImagePreview}" alt="Prescription preview" class="ocr-preview-img">
    <button class="btn-action" onclick="clearOcrResult()">✕ Clear</button>
  `;
  preview.style.display = '';
}

/**
 * Send image to Sarvam OCR endpoint.
 * The backend proxies to Sarvam's parse/document endpoint.
 *
 * @param {File} imageFile - Image to OCR
 */
async function processOcrImage(imageFile) {
  const loading = document.getElementById('ocrLoading');
  const resultArea = document.getElementById('ocrResultArea');
  if (loading) {
    loading.style.display = '';
    loading.innerHTML = '<div class="loading-spinner"></div><p>Parsing text... this may take up to 15-20 seconds.</p>';
  }
  if (resultArea) resultArea.innerHTML = '';

  try {
    // Convert to base64 for API
    const base64 = await fileToBase64(imageFile);

    const res = await fetch(apiUrl('/api/ocr'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: base64 }),
    });

    const data = await res.json();
    if (loading) loading.style.display = 'none';

    if (data.text || data.ocr_text) {
      const ocrText = data.text || data.ocr_text;
      ocrResult = { text: ocrText, medicines: [] };
      renderOcrText(ocrText);

      // Auto-extract medicines
      await extractMedicines(ocrText);
    } else {
      toast('Could not read prescription', 'error');
      if (resultArea) resultArea.innerHTML = '<p>No text detected. Try a clearer image.</p>';
    }
  } catch (err) {
    if (loading) loading.style.display = 'none';
    toast('OCR failed', 'error');
    console.error('OCR error:', err);
  }
}

function renderOcrText(text) {
  const resultArea = document.getElementById('ocrResultArea');
  if (!resultArea) return;

  resultArea.innerHTML = `
    <div class="ocr-raw-text">
      <h4>📄 Extracted Text</h4>
      <pre>${escapeHtml(text)}</pre>
      <button class="btn-action" onclick="searchOcrText()">🔍 Search This Text</button>
    </div>
  `;
}

// ─── Medicine Extraction ────────────────────────────────────────────────────

/**
 * Send OCR text to Sarvam LLM for medicine name extraction.
 * WHY a separate step: OCR gives raw text; LLM intelligently
 * identifies medicine names, dosages, and frequencies.
 *
 * @param {string} ocrText - Raw OCR text from prescription
 */
async function extractMedicines(ocrText) {
  const listContainer = document.getElementById('medicineChecklist');
  if (listContainer) listContainer.innerHTML = '<div class="loading-text">Extracting medicines...</div>';

  try {
    const res = await fetch(apiUrl('/api/search'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: `Extract all medicine/drug names from the following prescription text. Return ONLY a JSON array of objects with keys: name, dosage, frequency. Example: [{"name": "Paracetamol", "dosage": "500mg", "frequency": "twice daily"}]. Text:\n\n${ocrText}`,
        language: 'en-IN',
        extract_medicines: true,
      }),
    });

    const data = await res.json();
    const answer = data.answer || data.response || '';

    // Try to parse JSON array from response
    const medicines = parseMedicineList(answer);

    if (medicines.length > 0) {
      ocrResult.medicines = medicines.map(m => ({ ...m, checked: true }));
      renderMedicineChecklist();
    } else {
      if (listContainer) {
        listContainer.innerHTML = '<p>No medicines detected. Try searching the text manually.</p>';
      }
    }
  } catch (err) {
    console.error('Medicine extraction error:', err);
    if (listContainer) {
      listContainer.innerHTML = '<p>Could not extract medicines. Try searching manually.</p>';
    }
  }
}

/**
 * Parses LLM response to extract medicine JSON array.
 * The LLM may return JSON wrapped in markdown code blocks or text.
 *
 * @param {string} text - LLM response text
 * @returns {Array} Array of {name, dosage, frequency} objects
 */
function parseMedicineList(text) {
  // Try direct JSON parse
  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) return parsed;
  } catch {}

  // Try extracting JSON from markdown code block
  const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[1]);
      if (Array.isArray(parsed)) return parsed;
    } catch {}
  }

  // Try finding array in response
  const arrayMatch = text.match(/\[[\s\S]*\]/);
  if (arrayMatch) {
    try {
      const parsed = JSON.parse(arrayMatch[0]);
      if (Array.isArray(parsed)) return parsed;
    } catch {}
  }

  return [];
}

// ─── Medicine Checklist UI ──────────────────────────────────────────────────

function renderMedicineChecklist() {
  const container = document.getElementById('medicineChecklist');
  if (!container || !ocrResult?.medicines) return;

  const medicines = ocrResult.medicines;

  let html = `<h4>💊 Extracted Medicines (${medicines.length})</h4>`;
  html += medicines.map((m, i) => `
    <div class="medicine-item">
      <label class="medicine-checkbox">
        <input type="checkbox" ${m.checked ? 'checked' : ''} onchange="toggleMedicine(${i})">
        <span class="medicine-name">${escapeHtml(m.name)}</span>
      </label>
      <span class="medicine-dose">${escapeHtml(m.dosage || '')}</span>
      <span class="medicine-freq">${escapeHtml(m.frequency || '')}</span>
      <button class="btn-action small" onclick="searchSingleMedicine('${escapeHtml(m.name)}')">🔍</button>
    </div>
  `).join('');

  html += `
    <div class="medicine-actions">
      <button class="btn-primary" onclick="searchSelectedMedicines()">🔍 Search Selected</button>
      <button class="btn-secondary" onclick="checkAllMedicines(true)">Select All</button>
      <button class="btn-secondary" onclick="checkAllMedicines(false)">Deselect All</button>
    </div>
  `;

  container.innerHTML = html;
}

function toggleMedicine(index) {
  if (ocrResult?.medicines?.[index] !== undefined) {
    ocrResult.medicines[index].checked = !ocrResult.medicines[index].checked;
  }
}

function checkAllMedicines(checked) {
  if (ocrResult?.medicines) {
    ocrResult.medicines.forEach(m => m.checked = checked);
    renderMedicineChecklist();
  }
}

function searchSingleMedicine(name) {
  performSearch(`Drug information for ${name}: safety, dosage, side effects, contraindications`);
}

function searchSelectedMedicines() {
  const selected = ocrResult?.medicines?.filter(m => m.checked) || [];
  if (selected.length === 0) {
    toast('No medicines selected', 'error');
    return;
  }

  const names = selected.map(m => m.name).join(', ');
  performSearch(`Drug interaction and safety analysis for: ${names}`);
}

function searchOcrText() {
  if (ocrResult?.text) {
    performSearch(`Analyze this prescription: ${ocrResult.text}`);
  }
}

function clearOcrResult() {
  ocrResult = null;
  ocrImagePreview = null;
  const preview = document.getElementById('ocrPreview');
  const resultArea = document.getElementById('ocrResultArea');
  const checklist = document.getElementById('medicineChecklist');
  if (preview) { preview.innerHTML = ''; preview.style.display = 'none'; }
  if (resultArea) resultArea.innerHTML = '';
  if (checklist) checklist.innerHTML = '';
}

// ─── Utility ────────────────────────────────────────────────────────────────

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// ─── Init ───────────────────────────────────────────────────────────────────

function initOcr() {
  // File input
  const fileInput = document.getElementById('ocrFileInput');
  fileInput?.addEventListener('change', (e) => {
    if (e.target.files[0]) handleOcrFileSelect(e.target.files[0]);
  });

  // Camera button
  const cameraBtn = document.getElementById('ocrCameraBtn');
  cameraBtn?.addEventListener('click', () => {
    // Open camera on mobile via capture attribute
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment'; // Back camera
    input.onchange = (e) => handleOcrFileSelect(e.target.files[0]);
    input.click();
  });

  // Drag and drop on OCR zone
  const dropZone = document.getElementById('ocrDropZone');
  if (dropZone) {
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => {
      dropZone.classList.remove('dragover');
    });
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      const file = e.dataTransfer?.files?.[0];
      if (file) handleOcrFileSelect(file);
    });
  }
}
