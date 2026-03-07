/**
 * PharmAI Voice — Speech-to-Text and Text-to-Speech via Sarvam AI
 * STT: MediaRecorder → WAV → Sarvam Saaras v3
 * TTS: Text → Sarvam Bulbul v3 → Audio playback
 */

// ─── State ──────────────────────────────────────────────────────────────────
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let currentAudio = null;      // Currently playing audio element
let currentPlayBtn = null;    // Currently highlighted play button

// ─── STT: Voice Search ──────────────────────────────────────────────────────

/**
 * Toggle voice recording. When stopped, sends audio to Sarvam STT
 * and auto-populates the search bar with the transcript.
 *
 * WHY MediaRecorder + WAV: Sarvam STT expects proper WAV audio.
 * We record as webm and the server converts to WAV before sending.
 */
async function toggleVoiceSearch() {
  const micBtn = document.getElementById('micBtn');

  if (isRecording) {
    // Stop recording
    stopRecording();
    return;
  }

  // Start recording
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    audioChunks = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      // Release mic
      stream.getTracks().forEach(t => t.stop());

      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      await processSTT(blob);
    };

    mediaRecorder.start();
    isRecording = true;

    // Visual feedback
    micBtn?.classList.add('recording');
    toast('Listening... tap again to stop', 'info');

    // Auto-stop after 15 seconds to prevent accidental long recording
    setTimeout(() => {
      if (isRecording) stopRecording();
    }, 15000);

  } catch (err) {
    toast('Microphone access denied', 'error');
    console.error('Mic error:', err);
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  isRecording = false;
  document.getElementById('micBtn')?.classList.remove('recording');
}

/**
 * Send audio blob to Sarvam STT and populate search bar.
 *
 * @param {Blob} audioBlob - Recorded audio (webm format)
 */
async function processSTT(audioBlob) {
  showTypingIndicator('Transcribing...');

  try {
    // Convert blob to base64 for the API
    const reader = new FileReader();
    const base64 = await new Promise((resolve, reject) => {
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.onerror = reject;
      reader.readAsDataURL(audioBlob);
    });

    const res = await fetch(apiUrl('/api/stt'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        audio: base64,
        language: selectedLang || 'en-IN',
      }),
    });

    removeTypingIndicator();

    const data = await res.json();
    if (data.transcript) {
      const input = document.getElementById('searchInput');
      if (input) {
        input.value = data.transcript;
        input.focus();
      }
      toast('Voice captured!', 'success');

      // Auto-search if confident
      if (data.transcript.length > 5) {
        performSearch(data.transcript);
      }
    } else {
      toast('Could not understand audio', 'error');
    }
  } catch (err) {
    removeTypingIndicator();
    toast('Speech recognition failed', 'error');
    console.error('STT error:', err);
  }
}

// ─── TTS: Read Aloud ────────────────────────────────────────────────────────

/**
 * Play TTS for a given text using Sarvam Bulbul v3.
 * If audio is already playing, stop it first.
 *
 * @param {string} text - Text to speak
 * @param {HTMLElement} btn - The button element (for visual state)
 */
async function playTTS(text, btn) {
  // If same audio playing, toggle pause/play
  if (currentAudio && currentPlayBtn === btn) {
    if (currentAudio.paused) {
      currentAudio.play();
      btn?.classList.add('playing');
    } else {
      currentAudio.pause();
      btn?.classList.remove('playing');
    }
    return;
  }

  // Stop any previous audio
  stopTTS();

  if (!text) return;

  // Strip markdown and limit length for TTS
  const plain = text
    .replace(/[#*_`\[\]()]/g, '')
    .replace(/\n+/g, ' ')
    .trim()
    .slice(0, 500);

  btn?.classList.add('loading');

  try {
    const res = await fetch(apiUrl('/api/tts'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: plain, language: selectedLang || 'en-IN' }),
    });

    const data = await res.json();
    if (data.audio) {
      currentAudio = new Audio('data:audio/wav;base64,' + data.audio);
      currentPlayBtn = btn;

      currentAudio.onended = () => {
        btn?.classList.remove('playing');
        currentAudio = null;
        currentPlayBtn = null;
      };

      currentAudio.play();
      btn?.classList.remove('loading');
      btn?.classList.add('playing');
    } else {
      throw new Error('No audio returned');
    }
  } catch (err) {
    btn?.classList.remove('loading');
    toast('Text-to-speech failed', 'error');
    console.error('TTS error:', err);
  }
}

function stopTTS() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  if (currentPlayBtn) {
    currentPlayBtn.classList.remove('playing');
    currentPlayBtn = null;
  }
}

// ─── Init ───────────────────────────────────────────────────────────────────

function initVoice() {
  // Mic button
  document.getElementById('micBtn')?.addEventListener('click', toggleVoiceSearch);

  // Stop TTS when navigating away
  window.addEventListener('beforeunload', stopTTS);
}
