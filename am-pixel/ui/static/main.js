/* AM Pixel Web UI — main.js */

// ---------------------------------------------------------------------------
// Status bar
// ---------------------------------------------------------------------------
async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const hw = data.hardware || {};
    document.getElementById('hw-status').textContent =
      `Backend: ${hw.backend || '?'} | GPU: ${hw.gpu_model || 'N/A'} | VRAM: ${hw.vram_gb || 'N/A'}`;
    const phaseEl = document.getElementById('phase-status');
    if (phaseEl) phaseEl.textContent = data.phase || '';
  } catch (e) {
    const el = document.getElementById('hw-status');
    if (el) el.textContent = 'Status unavailable';
  }
}

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------
function initTabs() {
  const items = document.querySelectorAll('.tab-item');
  const label = document.getElementById('current-tab-label');
  items.forEach(item => {
    item.addEventListener('click', () => {
      items.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      if (label) label.textContent = item.textContent;
      // TODO: load asset grid for selected tab in Phase 7
    });
  });
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------
let _currentCandidateId = null;

function appendChat(role, text) {
  const log = document.getElementById('chat-log');
  if (!log) return;
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function initChat() {
  const input = document.getElementById('chat-input');
  const btn = document.getElementById('btn-send');
  if (!input || !btn) return;

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    appendChat('user', text);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      appendChat('assistant', data.reply || '…');

      if (data.candidate_id) {
        _currentCandidateId = data.candidate_id;
        showApprovalControls(true);
        // TODO: render preview canvases when generation engine connected
      }
    } catch (e) {
      appendChat('system', 'Error: ' + e.message);
    }
  }

  btn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
}

// ---------------------------------------------------------------------------
// Approval controls
// ---------------------------------------------------------------------------
function showApprovalControls(visible) {
  const el = document.getElementById('approval-controls');
  if (el) el.classList.toggle('hidden', !visible);
}

function initApproval() {
  const btnApprove = document.getElementById('btn-approve');
  const btnReject  = document.getElementById('btn-reject');
  const btnAdjust  = document.getElementById('btn-adjust');
  const adjustInput = document.getElementById('adjust-input');
  const btnSendAdj  = document.getElementById('btn-send-adjust');

  if (!btnApprove) return;

  async function sendAction(action, note) {
    if (!_currentCandidateId) return;
    try {
      const res = await fetch('/api/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, candidate_id: _currentCandidateId, adjustment_note: note || null }),
      });
      const data = await res.json();
      appendChat('system', `[${action.toUpperCase()}] ${data.reply}`);
      if (action !== 'adjust') {
        showApprovalControls(false);
        _currentCandidateId = null;
        if (adjustInput) adjustInput.classList.add('hidden');
      }
    } catch (e) {
      appendChat('system', 'Error: ' + e.message);
    }
  }

  btnApprove.addEventListener('click', () => sendAction('approve'));
  btnReject.addEventListener('click',  () => sendAction('reject'));

  btnAdjust.addEventListener('click', () => {
    if (adjustInput) adjustInput.classList.toggle('hidden');
  });

  if (btnSendAdj) {
    btnSendAdj.addEventListener('click', () => {
      const note = document.getElementById('adjust-note').value.trim();
      if (!note) return;
      sendAction('adjust', note);
      document.getElementById('adjust-note').value = '';
      if (adjustInput) adjustInput.classList.add('hidden');
    });
  }
}

// ---------------------------------------------------------------------------
// Canvas helpers (pixel-art rendering)
// ---------------------------------------------------------------------------
function clearCanvas(id) {
  const c = document.getElementById(id);
  if (!c) return;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#111';
  ctx.fillRect(0, 0, c.width, c.height);
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  loadStatus();
  initTabs();
  initChat();
  initApproval();
  clearCanvas('preview-1x');
  clearCanvas('preview-4x');
  clearCanvas('ff-preview-1x');
  clearCanvas('ff-preview-4x');

  // Refresh status every 30s
  setInterval(loadStatus, 30000);

  appendChat('system', 'AM Pixel ready. Describe what you want to generate.');
});
