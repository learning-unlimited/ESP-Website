// Shared helpers for all pages.

// The page's <main id="checkscan"> says where the module lives (e.g. /onsite/Splash/2026/).
const ROOT = document.getElementById('checkscan').dataset.base;
const PAGES = { index: 'checkscan', batch: 'checkscan_batch', finalize: 'checkscan_finalize', slips: 'checkscan_slips', history: 'checkscan_history' };

// URL of a page of this module, e.g. pageUrl('batch', batchId).
export const pageUrl = (page, id = '') => ROOT + PAGES[page] + '/' + id;
// URL of an API view: apiUrl('batches', id, 'op=finalize').
export const apiUrl = (name, id = '', query = '') => ROOT + 'checkscan_api_' + name + (id ? '/' + id : '') + (query ? '?' + query : '');

// {% csrf_token %} in the page renders the hidden input and makes Django set the cookie; prefer the input (the site renames the cookie to esp_csrftoken).
function csrfToken() {
  const input = document.querySelector('#checkscan input[name=csrfmiddlewaretoken]');
  if (input) return input.value;
  const c = document.cookie.split('; ').find(x => x.startsWith('esp_csrftoken='));
  return c ? decodeURIComponent(c.slice('esp_csrftoken='.length)) : '';
}

export async function api(path, { method = 'GET', json, form } = {}) {
  const opts = { method, headers: {}, credentials: 'same-origin' };
  if (method !== 'GET') opts.headers['X-CSRFToken'] = csrfToken();
  if (json !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(json); }
  if (form) opts.body = form;
  const r = await fetch(path, opts);
  const type = r.headers.get('Content-Type') || '';
  const body = type.includes('json') ? await r.json() : await r.text();
  if (!r.ok) {
    const err = new Error((body && body.error) || `${r.status} ${r.statusText}`);
    err.status = r.status; err.body = body;
    throw err;
  }
  return body;
}

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat()) if (c != null) e.append(c);
  return e;
}

// "150", "$1,250.5" -> "150.00" / "1250.50", or null if not a positive amount.
export function normAmount(v) {
  const s = String(v ?? '').replace(/[$,\s]/g, '');
  if (!/^\d+(\.\d{1,2})?$/.test(s) || +s <= 0) return null;
  return (+s).toFixed(2);
}

// "Splash 2026 · batch 3" (older batches without a program fall back to the internal id).
export const batchName = b => (b.program_name ? `${b.program_name} · batch ${b.program_batch}` : `batch #${b.id}`);

export const money = a => (a == null ? '—' : '$' + Number(a).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
export const when = iso => (iso ? new Date(iso).toLocaleString() : '');

// Top bar: just the start of the main flow and the history view.
export function header(active) {
  const nav = el('nav', { class: 'top' },
    ...[['index', 'Scan Checks'], ['history', 'History']].map(([page, label]) =>
      el('a', { href: pageUrl(page), class: page === active ? 'active' : '' }, label)));
  document.querySelector('main').prepend(nav);
}

// Left-to-right progress for the main flow:
// 1 choose batch -> 2 scan & enter amounts -> 3 finalize -> 4 deposit slips.
// A step is only clickable once it is reachable for this batch. Safe to call again after the batch changes.
export function steps(current, batch = null) {
  const id = batch ? batch.id : '';
  const items = [
    [pageUrl('index'), 'Choose batch', true, ''],
    [pageUrl('batch', id), 'Scan & enter amounts', !!batch, 'Choose a batch first'],
    [pageUrl('finalize', id), 'Finalize batch', !!batch && !batch.archived && (batch.ready || batch.finalized), batch && batch.archived ? 'This batch was deleted' : 'Every check needs an amount and check number first'],
    [pageUrl('slips', id), 'Deposit slips', !!batch && !batch.archived && batch.finalized, batch && batch.archived ? 'This batch was deleted' : 'Finalize the batch first'],
  ];
  const box = el('ol', { class: 'steps' }, ...items.map(([href, label, reachable, why], i) => {
    const n = i + 1;
    const cls = n === current ? 'current' : n < current ? 'done' : reachable ? '' : 'blocked';
    return el('li', { class: cls, title: reachable ? '' : why },
      n !== current && reachable ? el('a', { href }, label) : el('span', {}, label));
  }));
  const old = document.querySelector('ol.steps');
  if (old) old.replaceWith(box); else document.querySelector('main').prepend(box);
}

// Short message floating at the top of the page.
let toastTimer;
export function toast(text) {
  let t = document.getElementById('toast');
  if (!t) { t = el('div', { id: 'toast', role: 'alert' }); document.body.append(t); }
  t.textContent = text; t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 4000);
}

// Small "click twice to confirm" helper (the page has no confirm() dialogs).
export function confirmClick(button, label, action) {
  let armed = false, timer;
  const orig = button.textContent;
  button.addEventListener('click', async () => {
    if (!armed) {
      armed = true; button.textContent = typeof label === 'function' ? label() : label; button.classList.add('armed');
      timer = setTimeout(() => { armed = false; button.textContent = orig; button.classList.remove('armed'); }, 4000);
      return;
    }
    clearTimeout(timer); armed = false; button.textContent = orig; button.classList.remove('armed');
    await action();
  });
}

// A deposit slip shown as plain text, with a download button.
export function slipView(depositId) {
  const url = apiUrl('deposits', depositId, 'format=txt');
  const pre = el('pre', { class: 'sheet' }, 'loading…');
  fetch(url).then(r => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
    .then(t => (pre.textContent = t), e => (pre.textContent = "Couldn't load the slip: " + e.message));
  return el('div', { class: 'sheet-view' }, pre, el('a', { href: url + '&download=1', download: true, class: 'button small' }, 'Download (.txt)'));
}
