const promptInput = document.getElementById('promptInput');
const generateBtn = document.getElementById('generateBtn');
const statusSection = document.getElementById('statusSection');
const statusText = document.getElementById('statusText');
const resultSection = document.getElementById('resultSection');
const gifResult = document.getElementById('gifResult');
const downloadBtn = document.getElementById('downloadBtn');
const newBtn = document.getElementById('newBtn');
const errorSection = document.getElementById('errorSection');
const errorText = document.getElementById('errorText');
const retryBtn = document.getElementById('retryBtn');

let currentEventSource = null;

function showSection(name) {
  statusSection.classList.add('hidden');
  resultSection.classList.add('hidden');
  errorSection.classList.add('hidden');
  if (name === 'status') statusSection.classList.remove('hidden');
  if (name === 'result') resultSection.classList.remove('hidden');
  if (name === 'error') errorSection.classList.remove('hidden');
}

function setGenerating(active) {
  generateBtn.disabled = active;
  promptInput.disabled = active;
  generateBtn.querySelector('.btn-text').textContent = active ? 'Generating...' : 'Generate';
}

function generate() {
  const prompt = promptInput.value.trim();
  if (!prompt) {
    promptInput.focus();
    return;
  }

  if (currentEventSource) {
    currentEventSource.close();
    currentEventSource = null;
  }

  setGenerating(true);
  showSection('status');
  statusText.textContent = 'Starting...';

  const url = `/generate-stream?prompt=${encodeURIComponent(prompt)}`;
  const evtSource = new EventSource(url);
  currentEventSource = evtSource;

  evtSource.addEventListener('status', (e) => {
    const data = JSON.parse(e.data);
    statusText.textContent = data.message;
  });

  evtSource.addEventListener('complete', (e) => {
    const data = JSON.parse(e.data);
    evtSource.close();
    currentEventSource = null;

    gifResult.src = data.gifUrl;
    downloadBtn.href = data.gifUrl;
    downloadBtn.download = data.filename;

    showSection('result');
    setGenerating(false);
  });

  evtSource.addEventListener('error', (e) => {
    evtSource.close();
    currentEventSource = null;

    let message = 'Generation failed. Check the terminal for details.';
    try {
      const data = JSON.parse(e.data);
      if (data.message) message = data.message;
    } catch {}

    errorText.textContent = message;
    showSection('error');
    setGenerating(false);
  });

  // Fallback: if SSE itself errors (connection lost)
  evtSource.onerror = () => {
    if (evtSource.readyState === EventSource.CLOSED) return;
    evtSource.close();
    currentEventSource = null;
    errorText.textContent = 'Connection lost. Is the server running?';
    showSection('error');
    setGenerating(false);
  };
}

// Generate button
generateBtn.addEventListener('click', generate);

// Enter key in input
promptInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') generate();
});

// Suggestion pills
document.querySelectorAll('.pill').forEach(pill => {
  pill.addEventListener('click', () => {
    promptInput.value = pill.dataset.prompt;
    promptInput.focus();
  });
});

// Make another
newBtn.addEventListener('click', () => {
  showSection(null);
  promptInput.value = '';
  promptInput.focus();
});

// Retry
retryBtn.addEventListener('click', () => {
  showSection(null);
  generate();
});
