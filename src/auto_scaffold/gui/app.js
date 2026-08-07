let ws = null;
let currentProposals = [];

function updateStatusUI(connected) {
  const statusElement = document.getElementById('ws-status') || document.querySelector('.connection-status');
  if (statusElement) {
    statusElement.textContent = connected ? '● Connected' : '● Connecting...';
    statusElement.style.color = connected ? '#4ade80' : '#f87171';
  } else {
    document.querySelectorAll('span').forEach(el => {
      if (el.textContent.includes('Connect')) {
        el.textContent = connected ? '● Connected' : '● Connecting...';
        el.style.color = connected ? '#4ade80' : '#f87171';
      }
    });
  }
}

function connectWS() {
  const wsUrl = "ws://127.0.0.1:8765/ws";

  try {
    if (ws) {
      ws.onclose = null;
      ws.close();
    }

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      updateStatusUI(true);
      log('WebSocket connected cleanly', 'success');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'progress') {
          updateStepUI(data.step, data.message);
          log(`Step ${data.step}: ${data.message}`, data.message.includes('Error') ? 'error' : 'info');
        }
      } catch (e) {}
    };

    ws.onerror = () => updateStatusUI(false);
    ws.onclose = () => {
      updateStatusUI(false);
      setTimeout(connectWS, 2000);
    };
  } catch (e) {
    updateStatusUI(false);
    setTimeout(connectWS, 2000);
  }
}

function updateStepUI(stepNum, message) {
  // Find step container by attribute or numeric step badge
  let stepCard = document.querySelector(`[data-step="${stepNum}"]`);

  if (!stepCard) {
    const allCards = document.querySelectorAll('.step-card, .progress-item, div');
    allCards.forEach(card => {
      const text = card.textContent || '';
      if (text.includes(String(stepNum)) && (text.includes('Scan') || text.includes('Generate') || text.includes('Run') || text.includes('Propose') || text.includes('Review'))) {
        stepCard = card;
      }
    });
  }

  if (!stepCard) return;

  // Locate description paragraph inside card
  const desc = stepCard.querySelector('.step-desc, p, small') || stepCard;
  if (desc && desc !== stepCard) {
    desc.textContent = message;
  }

  stepCard.classList.remove('running', 'done', 'error');

  const lowerMsg = message.toLowerCase();
  if (lowerMsg.includes('failed') || lowerMsg.includes('error')) {
    stepCard.classList.add('error');
    stepCard.style.borderLeft = '4px solid #f87171';
  } else if (
    lowerMsg.includes('complete') || 
    lowerMsg.includes('passed') || 
    lowerMsg.includes('generated') || 
    lowerMsg.includes('ready') ||
    lowerMsg.includes('patched')
  ) {
    stepCard.classList.add('done');
    stepCard.style.borderLeft = '4px solid #4ade80';
    
    const badge = stepCard.querySelector('.step-number, div');
    if (badge) badge.style.backgroundColor = '#16a34a';
  } else {
    stepCard.classList.add('running');
    stepCard.style.borderLeft = '4px solid #38bdf8';
  }
}

function resetSteps() {
  document.querySelectorAll('[data-step]').forEach(card => {
    card.classList.remove('running', 'done', 'error');
    card.style.borderLeft = 'none';
  });
  const container = document.getElementById('proposals-container');
  if (container) container.style.display = 'none';
}

function log(msg, type = 'info') {
  const consoleBox = document.getElementById('console') || document.getElementById('logs') || document.querySelector('.console-box');
  if (!consoleBox) return;

  const time = new Date().toLocaleTimeString();
  const entry = document.createElement('div');
  entry.style.fontFamily = 'monospace';
  entry.style.fontSize = '12px';
  entry.style.marginBottom = '4px';

  if (type === 'error') entry.style.color = '#f87171';
  else if (type === 'success') entry.style.color = '#4ade80';
  else if (type === 'warning') entry.style.color = '#fbbf24';
  else entry.style.color = '#cbd5e1';

  entry.textContent = `[${time}] ${msg}`;
  consoleBox.appendChild(entry);
  consoleBox.scrollTop = consoleBox.scrollHeight;
}

function getFolder() {
  const input = document.getElementById('folder-path') || document.getElementById('folderPath') || document.querySelector('input[type="text"]');
  return input ? input.value.trim() : '';
}

function setButtons(disabled) {
  document.querySelectorAll('button:not(#stop-btn)').forEach(btn => btn.disabled = disabled);
}

async function api(endpoint, payload) {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'API Request Failed' }));
    throw new Error(err.detail || 'API Request Failed');
  }
  return response.json();
}

function renderProposals(proposals) {
  currentProposals = proposals || [];
  let container = document.getElementById('proposals-container');
  
  if (!container) {
    container = document.createElement('div');
    container.id = 'proposals-container';
    const reviewCard = document.querySelector('[data-step="5"]') || document.body;
    reviewCard.appendChild(container);
  }

  container.style.display = 'block';

  if (!proposals || proposals.length === 0) {
    container.innerHTML = '<div style="color: #94a3b8; margin-top: 10px;">No proposals.</div>';
    return;
  }

  container.innerHTML = proposals.map((p, idx) => `
    <div id="proposal-card-${p.id}" style="margin-top: 15px; padding: 12px; background: #1e293b; border: 1px solid #334155; border-radius: 6px;">
      <h4 style="color: #38bdf8; margin: 0 0 8px 0; font-size: 14px;">📁 Proposed Fix: ${p.target_file}</h4>
      <pre style="background: #0f172a; color: #4ade80; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; overflow-x: auto; margin: 0;"><code>${p.diff}</code></pre>
      <div style="margin-top: 10px; display: flex; gap: 8px;">
        <button style="background: #16a34a; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer;" onclick="approveFix('${p.id}', '${p.target_file}', ${idx})">Approve Fix</button>
        <button style="background: #dc2626; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer;" onclick="rejectFix('${p.id}')">Reject</button>
      </div>
    </div>
  `).join('');
}

async function approveFix(propId, targetFile, index) {
  const folder = getFolder();
  if (!folder) return alert("Folder path is required!");

  const proposal = currentProposals[index];
  if (!proposal) return;

  setButtons(true);
  try {
    const res = await api('/api/apply-fix', {
      folder: folder,
      target_file: targetFile,
      diff: proposal.diff
    });

    log(res.message, 'success');
    const card = document.getElementById(`proposal-card-${propId}`);
    if (card) card.remove();

  } catch (e) {
    log(`Failed to apply fix: ${e.message}`, 'error');
  } finally {
    setButtons(false);
  }
}

function rejectFix(propId) {
  const card = document.getElementById(`proposal-card-${propId}`);
  if (card) card.remove();
  log(`Proposal ${propId} rejected`, 'error');
}

async function runStep(endpoint) {
  const folder = getFolder();
  if (!folder) return alert('Enter folder path');
  setButtons(true);
  try {
    const res = await api(endpoint, { folder });
    if (res.proposals) renderProposals(res.proposals);
  } catch (e) {
    log(e.message, 'error');
  } finally {
    setButtons(false);
  }
}

async function runPipeline() {
  const folder = getFolder();
  if (!folder) return alert('Enter folder path');
  
  resetSteps();
  setButtons(true);

  try {
    const res = await api('/api/pipeline', { folder });
    if (res.proposals && res.proposals.length > 0) {
      log(`Pipeline generated ${res.proposals.length} proposal(s).`, 'warning');
      renderProposals(res.proposals);
    } else {
      log('All tests passed!', 'success');
    }
  } catch (e) {
    log(e.message, 'error');
  } finally {
    setButtons(false);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  connectWS();

  const buttons = Array.from(document.querySelectorAll('button'));
  buttons.forEach(btn => {
    const text = btn.textContent.trim().toLowerCase();
    if (text.includes('scan')) btn.onclick = () => runStep('/api/scan');
    else if (text.includes('generate')) btn.onclick = () => runStep('/api/generate-tests');
    else if (text.includes('run tests')) btn.onclick = () => runStep('/api/run-tests');
    else if (text.includes('propose')) btn.onclick = () => runStep('/api/propose-fixes');
    else if (text.includes('pipeline')) btn.onclick = runPipeline;
  });
});