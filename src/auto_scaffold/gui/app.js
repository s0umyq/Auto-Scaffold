const ws = new WebSocket(`ws://${location.host}/ws`);
const logs = document.getElementById('logs');
const steps = document.querySelectorAll('.step');
let currentPipeline = false;
let abortController = null;

ws.onopen = () => log('Connected to server', 'success');
ws.onclose = () => { document.getElementById('connStatus').textContent = '● Disconnected'; document.getElementById('connStatus').style.color = '#f85149'; };
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === 'progress') handleProgress(msg);
};

function log(msg, type = 'info') {
  const time = new Date().toLocaleTimeString();
  const div = document.createElement('div');
  div.className = `log-entry ${type}`;
  div.innerHTML = `<span class="log-time">${time}</span><span>${msg}</span>`;
  logs.appendChild(div);
  logs.scrollTop = logs.scrollHeight;
}

function handleProgress(msg) {
  const stepEl = document.querySelector(`.step[data-step="${msg.step}"]`);
  if (!stepEl) return;
  const icon = stepEl.querySelector('.step-icon');
  const bar = stepEl.querySelector('.step-progress-bar');
  const title = stepEl.querySelector('.step-message');

  if (msg.message.includes('Complete') || msg.message.includes('pass') || msg.message.includes('Done')) {
    icon.className = 'step-icon done'; bar.style.width = '100%';
  } else if (msg.message.includes('Error') || msg.message.includes('Failed')) {
    icon.className = 'step-icon error'; bar.style.width = '0%';
  } else {
    icon.className = 'step-icon running'; bar.style.width = '50%';
  }
  title.textContent = msg.message;
  log(`${msg.step}: ${msg.message}`, msg.message.includes('Error') ? 'error' : 'info');
}

function resetSteps() {
  steps.forEach(s => {
    s.querySelector('.step-icon').className = 'step-icon pending';
    s.querySelector('.step-progress-bar').style.width = '0%';
  });
  logs.innerHTML = '';
}

function setButtons(disabled) {
  ['btnScan','btnGenTests','btnRunTests','btnPropose','btnPipeline'].forEach(id => {
    document.getElementById(id).disabled = disabled;
  });
  document.getElementById('btnStop').disabled = !disabled;
}

async function api(path, body) {
  const res = await fetch(path, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body), signal: abortController?.signal
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function getFolder() { return document.getElementById('folder').value.trim(); }

async function runScan() {
  const folder = getFolder(); if (!folder) return alert('Enter folder path');
  resetSteps(); setButtons(true); abortController = new AbortController();
  try {
    const res = await api('/api/scan', { folder });
    log(`Language: ${res.language}, PM: ${res.package_manager}, FW: ${res.test_framework}`, 'success');
    document.getElementById('btnGenTests').disabled = false;
    document.getElementById('btnRunTests').disabled = false;
    document.getElementById('btnPropose').disabled = false;
    document.getElementById('btnPipeline').disabled = false;
  } catch (e) { log(e.message, 'error'); }
  setButtons(false);
}

async function runGenerateTests() {
  const folder = getFolder(); if (!folder) return;
  resetSteps(); setButtons(true); abortController = new AbortController();
  try {
    await api('/api/generate-tests', { folder });
    log('Tests generated', 'success');
  } catch (e) { log(e.message, 'error'); }
  setButtons(false);
}

async function runTests() {
  const folder = getFolder(); if (!folder) return;
  resetSteps(); setButtons(true); abortController = new AbortController();
  try {
    await api('/api/run-tests', { folder });
    log('Tests completed', 'success');
  } catch (e) { log(e.message, 'error'); }
  setButtons(false);
}

async function runPropose() {
  const folder = getFolder(); if (!folder) return;
  resetSteps(); setButtons(true); abortController = new AbortController();
  try {
    const res = await api('/api/propose-fixes', { folder });
    log(`${res.approved} approved, ${res.applied} applied`, 'success');
  } catch (e) { log(e.message, 'error'); }
  setButtons(false);
}

async function runPipeline() {
  const folder = getFolder(); if (!folder) return;
  resetSteps(); setButtons(true); currentPipeline = true; abortController = new AbortController();
  try {
    const res = await api('/api/pipeline', { folder });
    if (res.proposals_count > 0) showProposals(res.proposals, folder);
    else log('All tests pass!', 'success');
  } catch (e) { log(e.message, 'error'); }
  setButtons(false); currentPipeline = false;
}

function showProposals(proposals, folder) {
  const container = document.createElement('div');
  container.className = 'panel';
  container.innerHTML = '<h2>Fix Proposals</h2><div class="proposals"></div>';
  const list = container.querySelector('.proposals');
  proposals.forEach(p => {
    const div = document.createElement('div');
    div.className = 'proposal';
    div.innerHTML = `<div class="proposal-header"><span class="proposal-file">${p.target_file}</span><div class="proposal-actions"><button class="btn btn-primary" onclick="applyOne('${p.id}','${folder}')">Apply</button><button class="btn btn-danger" onclick="rejectOne('${p.id}','${folder}')">Reject</button></div></div><div class="proposal-diff">${escapeHtml(p.diff)}</div>`;
    list.appendChild(div);
  });
  document.querySelector('main').appendChild(container);
}

function escapeHtml(text) {
  return text.replace(/&/g,'&').replace(/</g,'<').replace(/>/g,'>')
    .replace(/\+(.+)/g, '<span class="diff-add">+$1</span>')
    .replace(/\-(.+)/g, '<span class="diff-remove">-$1</span>');
}

function stopAll() {
  if (abortController) abortController.abort();
  currentPipeline = false;
  log('Stopped', 'warning');
  setButtons(false);
}