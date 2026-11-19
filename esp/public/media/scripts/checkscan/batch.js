import { api, $, el, header, steps, toast, normAmount, money, when, confirmClick, batchName, pageUrl, apiUrl } from './common.js';
import { SecureLink, BatchScanner, DEFAULT_HOST, prepareUpload, treasurerKey } from './scanner.js';

const batchId = document.getElementById('checkscan').dataset.batchId || '';
if (!batchId) location.href = pageUrl('index');
header('index');
steps(2, { id: batchId });

let batch = null;
let checks = [];      // this batch's checks, scan order
let amounts = [];     // [{amount, count}] most used first (all batches)
let selectedId = null;

// ================================================================ data

async function loadBatch() {
  batch = await api(apiUrl('batches', batchId));
  document.title = `${batchName(batch)} · ESP check scanner`;
  $('#batch-title').textContent = batchName(batch);
  const entered = batch.n_live - batch.n_need_amount;
  $('#batch-stats').textContent = `${batch.n_live} checks · ${entered} with amount` +
    (batch.n_need_amount ? ` · ${batch.n_need_amount} still need one` : ' · all entered') +
    ` · total ${money(batch.total)}` + (batch.done ? ' · deposited' : '');
  if (document.activeElement !== $('#batch-note')) $('#batch-note').value = batch.note;
  $('#batch-note').disabled = batch.finalized || batch.archived;
  const closed = batch.finalized || batch.archived;
  $('#closed').hidden = !closed; $('#scanner-panel').hidden = closed;
  $('#restore-batch').hidden = !batch.archived;
  $('#closed-title').textContent = batch.archived ? 'Deleted' : 'Finalized';
  if (batch.archived) {
    $('#closed-text').textContent = `Deleted ${when(batch.archived_at)} by ${batch.archived_by}. Restore it if this was a mistake.`;
  } else $('#closed-text').replaceChildren('This batch is finalized: no more scanning or changes. ', el('span', { id: 'closed-detail' }));
  if (!batch.archived) $('#closed-detail').replaceChildren(batch.done
    ? el('span', {}, 'Its deposit slips are on ', el('a', { href: pageUrl('slips', batchId) }, 'step 4'),
        '. If an error is found, discard the slips there and reopen the batch for edits on step 3.')
    : el('span', {}, 'To change something, reopen it on ', el('a', { href: pageUrl('finalize', batchId) }, 'step 3'), '.'));
  steps(2, batch);
  const canGo = !batch.archived && (batch.ready || batch.finalized);
  $('#next-link').href = batch.finalized ? pageUrl('slips', batchId) : pageUrl('finalize', batchId);
  $('#next-link').textContent = batch.finalized ? 'Next: deposit slips →' : 'Next: finalize batch →';
  $('#next-link').classList.toggle('disabled-look', !canGo);
  $('#next-why').textContent = canGo ? '' : nextBlocker();
  const hasScans = batch.n_checks > 0;
  $('#originals').classList.toggle('disabled', !hasScans);
  $('#originals').title = hasScans ? 'Originals and MICR, encrypted to the treasurer key' : 'No scans in this batch yet';
  if (hasScans) $('#originals').href = apiUrl('zip', batchId); else $('#originals').removeAttribute('href');
  $('#delete-batch').hidden = batch.finalized || batch.archived;
}

function nextBlocker() {
  if (batch && batch.archived) return 'This batch was deleted — restore it to continue.';
  if (!batch || !batch.n_live) return 'Scan some checks first.';
  const parts = [];
  if (batch.n_need_amount) parts.push(`${batch.n_need_amount} check(s) need an amount`);
  if (batch.n_need_checknum) parts.push(`${batch.n_need_checknum} need a check number`);
  if (batch.n_need_confirm) parts.push(`${batch.n_need_confirm} need payee/signature/endorsement confirmed`);
  return parts.join(', ') + ' before finalizing.';
}
$('#next-link').addEventListener('click', e => {
  if (batch && !batch.archived && (batch.ready || batch.finalized)) return;
  e.preventDefault(); e.stopImmediatePropagation();
  toast(nextBlocker());
}, true);

// Quick-amount buttons: amounts used so far in this batch's program.
const fetchAmounts = () => api(apiUrl('info')).then(info => info.amounts);

async function loadChecks() {
  [checks, amounts] = await Promise.all([api(apiUrl('checks', batchId)), fetchAmounts()]);
  if (selectedId == null || !checks.some(c => c.id === selectedId)) {
    const first = checks.find(incomplete) || checks[0];
    selectedId = first ? first.id : null;
    renderList(true); renderEditor(true);
  } else {
    renderList(); renderEditor(false);
  }
  loadBatch();
}

const needsAmount = c => !c.voided && c.amount == null;
// What a (non-voided) check still needs before the batch can be finalized.
function missing(c) {
  if (c.voided) return [];
  const m = [];
  if (c.amount == null) m.push('amount');
  if (!c.check_number) m.push('check #');
  if (!c.payee_ok) m.push('payee');
  if (!c.signed_ok) m.push('signature');
  if (!c.endorsed_ok) m.push('endorsement');
  return m;
}
const incomplete = c => missing(c).length > 0;
const selected = () => checks.find(c => c.id === selectedId) || null;

// ================================================================ list

function renderList(scroll = false) {
  $('#list-empty').hidden = checks.length > 0;
  $('#list tbody').replaceChildren(...checks.map((c, i) => {
    const m = missing(c);
    const status = c.voided ? 'removed' : c.deposit ? 'deposited' : m.length ? 'needs ' + m.join(', ') : '✓';
    const tr = el('tr', { class: ['clickable', c.id === selectedId ? 'selected' : '', c.voided ? 'voided' : ''].join(' '),
                          onclick: () => select(c.id) },
      el('td', {}, String(c.seq)),
      el('td', { class: !c.check_number && !c.voided ? 'needs' : '' }, c.check_number || '—'),
      el('td', { class: 'num' + (needsAmount(c) ? ' needs' : '') }, c.amount == null ? '—' : money(c.amount)),
      el('td', { class: 'status ' + (m.length ? 'hint bad' : 'hint ok'), title: status }, status));
    return tr;
  }));
  const row = $('#list tr.selected');
  if (scroll && row) row.scrollIntoView({ block: 'nearest' });
}

function select(id) {
  if (id == null) return;
  selectedId = id;
  renderList(true); renderEditor(true);
}

function move(delta) {
  const i = checks.findIndex(c => c.id === selectedId);
  const j = i + delta;
  if (j >= 0 && j < checks.length) select(checks[j].id);
}

// Once the current check has everything, go to the next one (after it, wrapping) that still needs
// something; otherwise stay and say what's left on this one.
function advanceIfDone() {
  const c = selected();
  if (c && incomplete(c)) {
    renderList(); renderEditor(false);
    msg('', ''); $('#amount-msg').replaceChildren(el('span', { class: 'bad' }, 'Still needed on this check: ' + missing(c).join(', ')));
    return;
  }
  const i = checks.findIndex(x => x.id === selectedId);
  const order = [...checks.slice(i + 1), ...checks.slice(0, i)];
  const nxt = order.find(incomplete);
  if (nxt) select(nxt.id);
  else { renderList(); renderEditor(false); msg('ok', 'Every check in this batch is done — you can finalize it.'); }
}

// ================================================================ editor

function msg(cls, text) { $('#amount-msg').replaceChildren(text ? el('span', { class: cls }, text) : ''); }

function renderButtons(disabled) {
  const sorted = [...amounts].sort((a, b) => a.amount - b.amount);
  $('#amount-buttons').replaceChildren(...sorted.map(a =>
    el('button', { class: 'amount' + (selected() && selected().amount === a.amount ? ' current' : ''),
                   disabled, onclick: () => save(a.amount), title: `used ${a.count}×` },
      money(a.amount))));
}

function renderEditor(newSelection) {
  const c = selected();
  $('#editor-empty').hidden = !!c; $('#editor').hidden = !c;
  if (!c) return;
  const i = checks.findIndex(x => x.id === c.id);
  $('#cur-id').textContent = String(c.seq);
  $('#cur-pos').textContent = `${i + 1} of ${checks.length} · scanned ${when(c.scanned_at)} by ${c.scanned_by}`;
  $('#cur-amount').textContent = c.amount == null ? 'enter below' : money(c.amount);
  $('#cur-amount').className = c.amount == null ? 'hint' : 'big';
  const closed = batch && (batch.finalized || batch.archived);
  const locked = c.voided || !!c.deposit || closed;
  $('#clear-amount').hidden = c.amount == null || locked;
  for (const [btn, flag, label] of [['#ok-payee', 'payee_ok', 'Made out to MIT ESP'], ['#ok-signed', 'signed_ok', 'Signed'], ['#ok-endorsed', 'endorsed_ok', 'Endorsed']]) {
    $(btn).setAttribute('aria-pressed', String(c[flag]));
    $(btn).textContent = (c[flag] ? '✓ ' : '') + label;
  }
  $('#cur-status').replaceChildren(c.voided ? el('span', { class: 'pill bad' }, 'removed') : c.deposit ? el('span', { class: 'pill' }, 'deposited') : '');
  $('#edit-controls').hidden = locked;
  $('#locked').hidden = !locked;
  $('#locked').textContent = closed ? (batch.archived ? 'This batch was deleted; restore it to make changes.' : 'This batch is finalized; its checks can no longer be changed.') : c.voided ? 'This check was removed from the batch (it stays on record). Restore it to edit.' : c.deposit ? 'This check is on a deposit and can no longer be changed.' : '';
  $('#void').textContent = c.voided ? 'Restore' : 'Remove';
  $('#void').title = c.voided ? 'Put this check back in the batch' : 'Leave this check out of the batch (e.g. a double scan, or not made out to MIT ESP) — kept on record, can be restored';
  $('#void').disabled = !!c.deposit || closed;
  $('#prev').disabled = i <= 0; $('#next').disabled = i >= checks.length - 1;
  renderButtons(locked);
  // Someone else changed the check number: show it unless this person is typing in the box.
  if (!newSelection && document.activeElement !== $('#cur-checknum')) $('#cur-checknum').value = c.check_number;
  if (newSelection) {
    msg('', '');
    $('#cur-checknum').value = c.check_number;
    $('#manual-amount').value = '';
    const bad = !c.micr_complete || !c.check_number;
    $('#checknum-warn').hidden = !bad; $('#cur-checknum').classList.toggle('needs', !c.check_number);
    // Never leave the previous check's images up while the next ones load.
    const img = $('#cur-img'), rear = $('#cur-rear');
    img.removeAttribute('src'); rear.removeAttribute('src');
    $('#rear-caption').textContent = 'Back';
    img.src = apiUrl('check', c.id, `file=redacted&v=${encodeURIComponent(c.scanned_at)}`);
    rear.src = apiUrl('check', c.id, `file=rear&v=${encodeURIComponent(c.scanned_at)}`);
    if (!locked) (c.check_number ? $('#manual-amount') : $('#cur-checknum')).focus({ preventScroll: true });
  }
}

// Every edit names the version it started from; if someone else saved in between, the server refuses
// and returns the current check, which replaces ours so the person sees what changed.
// Edits are sent one at a time, each with the newest version we know: two quick edits from this tab (a
// check number's change event followed by an amount click, a double click) would otherwise both carry the
// same version, and the second would be refused as a conflict with ourselves.
let patchChain = Promise.resolve();
function patch(c, body) {
  const run = patchChain.then(() => sendPatch(c.id, body));
  patchChain = run.catch(() => {});
  return run;
}

async function sendPatch(id, body) {
  const cur = checks.find(x => x.id === id);
  if (!cur) throw new Error('This check is no longer in the batch');
  try {
    const updated = await api(apiUrl('check', id), { method: 'PATCH', json: { ...body, version: cur.version } });
    checks[checks.findIndex(x => x.id === id)] = updated;
    return updated;
  } catch (e) {
    if (e.status === 409 && e.body && e.body.check) {
      checks[checks.findIndex(x => x.id === id)] = e.body.check;
      renderList(); renderEditor(false);
      if (document.activeElement !== $('#cur-checknum')) $('#cur-checknum').value = e.body.check.check_number;
      loadBatch();
    }
    throw e;
  }
}

async function save(amount) {
  const c = selected();
  if (!c || c.voided || c.deposit) return;
  const a = normAmount(amount);
  if (!a) return msg('bad', 'Enter an amount like 75 or 1,250.00');
  const checknum = $('#cur-checknum').value.trim();
  if (!checknum) { msg('bad', 'Type the check number first'); $('#cur-checknum').focus(); return; }
  try {
    await patch(c, { amount: a, check_number: checknum });
    amounts = await fetchAmounts();
    loadBatch();
    advanceIfDone();
  } catch (e) {
    msg('bad', 'Save failed: ' + e.message);
  }
}

async function toggleConfirm(flag) {
  const c = selected();
  if (!c || c.voided || (batch && batch.finalized)) return;
  try {
    const turnedOn = !c[flag];
    await patch(c, { [flag]: turnedOn });
    loadBatch();
    if (turnedOn && selected().amount != null) advanceIfDone(); else { renderList(); renderEditor(false); }
  } catch (e) { msg('bad', 'Save failed: ' + e.message); }
}
$('#ok-payee').addEventListener('click', () => toggleConfirm('payee_ok'));
$('#ok-signed').addEventListener('click', () => toggleConfirm('signed_ok'));
$('#ok-endorsed').addEventListener('click', () => toggleConfirm('endorsed_ok'));
// Click an image to see it full size.
for (const id of ['#cur-img', '#cur-rear']) {
  $(id).addEventListener('click', () => { if (!$(id).src) return; $('#zoom-img').src = $(id).src; $('#zoom-dialog').showModal(); });
}
// Close the enlarged image by clicking it, or anywhere outside it (the backdrop counts as the dialog itself).
$('#zoom-dialog').addEventListener('click', e => {
  if (e.target === $('#zoom-img') || e.target === $('#zoom-dialog')) $('#zoom-dialog').close();
});
$('#cur-rear').addEventListener('error', () => { if ($('#cur-rear').getAttribute('src')) $('#rear-caption').textContent = 'Back — not kept for checks scanned before this was added'; });

async function clearAmount() {
  const c = selected();
  if (!c || c.amount == null) return;
  try {
    await patch(c, { amount: null });
    amounts = await fetchAmounts();
    renderList(); renderEditor(false); loadBatch();
    msg('ok', 'Amount cleared — this check now needs an amount again.');
  } catch (e) { msg('bad', 'Clear failed: ' + e.message); }
}
$('#clear-amount').addEventListener('click', clearAmount);

async function saveCheckNumber() {
  const c = selected(), n = $('#cur-checknum').value.trim();
  if (!c || !n || n === c.check_number) return;
  try { await patch(c, { check_number: n }); $('#cur-checknum').classList.remove('needs'); renderList(); msg('ok', 'Check number saved'); }
  catch (e) { msg('bad', 'Save failed: ' + e.message); }
}

$('#manual-amount').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); save($('#manual-amount').value); } });
$('#cur-checknum').addEventListener('keydown', async e => {
  if (e.key === 'Enter') { e.preventDefault(); await saveCheckNumber(); $('#manual-amount').focus(); }
});
$('#cur-checknum').addEventListener('change', saveCheckNumber);
$('#prev').addEventListener('click', () => move(-1));
$('#next').addEventListener('click', () => move(1));
confirmClick($('#void'), () => (selected() && selected().voided ? 'Click again to restore' : 'Click again to remove'), async () => {
  const c = selected(); if (!c) return;
  try { await patch(c, { voided: !c.voided }); amounts = await fetchAmounts(); renderList(); renderEditor(false); loadBatch(); }
  catch (e) { msg('bad', e.message); }
});
async function saveNote() {
  const v = $('#batch-note').value.trim();
  if (!batch || v === batch.note) return;
  try { await api(apiUrl('batches', batchId), { method: 'PATCH', json: { note: v } }); batch.note = v; $('#note-msg').textContent = 'saved'; }
  catch (e) { $('#note-msg').textContent = 'not saved: ' + e.message; }
  setTimeout(() => ($('#note-msg').textContent = ''), 2500);
}
$('#batch-note').addEventListener('change', saveNote);
$('#batch-note').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); $('#batch-note').blur(); } });

confirmClick($('#delete-batch'), 'Click again to delete', async () => {
  if (scanner) return showError('Stop scanning before deleting the batch.');
  try {
    await api(apiUrl('batches', batchId, 'op=archive'), { method: 'POST' });
    location.href = pageUrl('index');
  } catch (e) { showError(`Couldn't delete the batch: ${e.message}`); }
});
$('#restore-batch').addEventListener('click', async () => {
  try { await api(apiUrl('batches', batchId, 'op=restore'), { method: 'POST' }); await loadBatch(); renderList(); renderEditor(false); }
  catch (e) { showError(`Couldn't restore the batch: ${e.message}`); }
});
document.addEventListener('keydown', e => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    if (e.target.matches('select, textarea')) return;
    e.preventDefault(); move(e.key === 'ArrowUp' ? -1 : 1); return;
  }
});

// ================================================================ scanner

let host = DEFAULT_HOST;
try { host = localStorage.getItem('scannerHost') || DEFAULT_HOST; } catch (e) { /* storage blocked */ }
$('#host').value = host;
$('#host').addEventListener('change', () => {
  host = $('#host').value.trim().replace(/\/$/, '');
  try { localStorage.setItem('scannerHost', host); } catch (e) { /* ignore */ }
  checkReachable();
});

let scanner = null;
let scanRun = Promise.resolve();
function setState(text, cls = '') {
  const s = $('#scanner-state');
  const working = /…$/.test(text);   // "stopping…", "connecting…"
  s.replaceChildren(working ? el('span', { class: 'spinner' }) : '', text);
  s.className = 'pill ' + (working ? 'wait big-state' : cls);
}

async function checkReachable() {
  $('#trust-link').href = host + '/';
  try {
    const st = await new SecureLink(host).status();
    $('#unreachable').hidden = true;
    if (!scanner) setState(st.FeederEmpty === 'false' ? 'ready — checks loaded' : 'ready', 'ok');
    $('#start').disabled = !!scanner;
  } catch (e) {
    $('#unreachable').hidden = false;
    if (!scanner) setState('not reachable', 'bad');
    $('#start').disabled = true;
  }
}
setInterval(() => { if (!scanner) checkReachable(); }, 3000);
checkReachable();

const stats = { scanned: 0, uploaded: 0, failed: [] };
let chain = Promise.resolve();
function renderStats() {
  const pending = stats.scanned - stats.uploaded - stats.failed.length;
  $('#upload-stats').replaceChildren(stats.scanned ? `This session: ${stats.scanned} scanned, ${stats.uploaded} saved${pending > 0 ? `, ${pending} saving…` : ''}` : '');
  if (stats.failed.length) {
    $('#upload-stats').append(el('div', { class: 'bad' }, `${stats.failed.length} failed to save — the data is kept in this tab. `,
      el('button', { onclick: retryFailed }, 'Retry')));
  }
}
function showError(m) { $('#errors').prepend(el('div', { class: 'banner bad' }, `${new Date().toLocaleTimeString()}: ${m}`)); }

async function uploadWithRetry(form) {
  let last;
  for (let i = 0; i < 3; i++) {
    try { return await api(apiUrl('checks', batchId), { method: 'POST', form }); }
    catch (e) { last = e; await new Promise(r => setTimeout(r, 1000 * (i + 1))); }
  }
  throw last;
}

function enqueue(item) {
  stats.scanned++; renderStats();
  chain = chain.then(async () => {
    try {
      const created = await uploadWithRetry(await prepareUpload(item));
      stats.uploaded++;
      checks.push(created);
      // If the check on screen is already done (or nothing is selected), show the new one;
      // otherwise leave the user where they are.
      const cur = selected();
      if (!cur || !incomplete(cur)) select(created.id); else renderList();
      loadBatch();
    } catch (e) {
      stats.failed.push(item);
      showError('Saving a scanned check failed: ' + e.message);
    }
    renderStats();
  });
}
function retryFailed() {
  const items = stats.failed.splice(0);
  stats.scanned -= items.length;
  items.forEach(enqueue);
}

// Only one tab on this computer may scan at a time (Web Locks are shared by all tabs of this site);
// the scanner's exclusive session then keeps other computers out too.
$('#start').addEventListener('click', () => {
  $('#start').disabled = true;
  if (!navigator.locks) return runScan();
  navigator.locks.request('esp-check-scanner', { ifAvailable: true }, async lock => {
    if (!lock) {
      showError('Another tab on this computer is already scanning. Stop it there first.');
      checkReachable();
      return;
    }
    await runScan();
  });
});

// The scanner session this computer last opened, kept in localStorage so the next Start can end it if
// its tab was closed or crashed mid-scan (otherwise the scanner stays locked until its session times out).
const SESSION_KEY = 'scannerSession';
function rememberSession(sid) {
  try {
    if (sid) localStorage.setItem(SESSION_KEY, JSON.stringify({ host, sid }));
    else localStorage.removeItem(SESSION_KEY);
  } catch (e) { /* storage blocked: rely on the scanner's timeout */ }
}
async function releaseLeftoverSession() {
  let left = null;
  try { left = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); } catch (e) { /* ignore */ }
  if (!left || !left.sid) return;
  setState('freeing scanner…');
  await new SecureLink(left.host || host).releaseSession(left.sid);
  rememberSession(null);
}

async function runScan() {
  try {
    await treasurerKey();
    // We hold the tab lock, so no other tab on this computer is scanning: a remembered session is a leftover.
    if (navigator.locks) await releaseLeftoverSession();
    $('#stop').disabled = false;
    scanner = new BatchScanner(new SecureLink(host), {
      onSession: rememberSession,
      onDocument: enqueue,
      onState: t => setState(t, t === 'scanning' ? 'ok' : t.startsWith('feeder') ? 'wait' : ''),
      onError: showError,
    });
    scanRun = scanner.run();
    await scanRun;
  } catch (e) {
    showError(e.message);
  } finally {
    scanner = null; $('#stop').disabled = true; checkReachable();
  }
}
$('#stop').addEventListener('click', () => { if (scanner) { $('#stop').disabled = true; scanner.stop(); } });
// Links off this page are blocked while scanning or while scans are still saving: the user stops
// the scan themselves. (Closing the tab / reloading gets the browser's own prompt — that can't be replaced.)
function leaveBlocker() {
  const pending = stats.scanned - stats.uploaded - stats.failed.length;
  if (scanner) return 'Scanning is still running — press Stop (and wait for it to finish) before leaving this page.';
  if (pending > 0) return `Wait — ${pending} scanned check(s) are still saving.`;
  if (stats.failed.length) return `${stats.failed.length} scanned check(s) didn't save. Press Retry before leaving, or they'll need rescanning.`;
  return '';
}
document.addEventListener('click', e => {
  const a = e.target.closest('a[href]');
  if (!a || a.target || a.hasAttribute('download')) return;
  const why = leaveBlocker();
  if (!why) return;
  e.preventDefault();
  toast(why);
  if (scanner) { $('#stop').classList.add('attention'); setTimeout(() => $('#stop').classList.remove('attention'), 2400); }
});

// Leaving or closing the page mid-scan: tell the scanner to stop feeding and end the session.
window.addEventListener('pagehide', () => { if (scanner) scanner.sl.release(); });
window.addEventListener('beforeunload', e => {
  if (scanner || stats.failed.length || stats.uploaded + stats.failed.length < stats.scanned) { e.preventDefault(); e.returnValue = ''; }
});

// Pick up other people's changes every few seconds (also while scanning).
setInterval(() => { if (!document.hidden) loadChecks().catch(() => {}); }, 5000);

loadBatch().then(loadChecks).catch(e => { $('#batch-title').textContent = 'Batch not found'; showError(e.message); });
