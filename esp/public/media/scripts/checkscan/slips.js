import { api, $, $$, el, header, steps, normAmount, money, when, batchName, slipView, confirmClick, pageUrl, apiUrl } from './common.js';

const batchId = document.getElementById('checkscan').dataset.batchId || '';
if (!batchId) location.href = pageUrl('index');
header('index');
steps(4, { id: batchId });
$('#back').href = pageUrl('finalize', batchId);

const cents = a => Math.round(+a * 100);
let checks = [];                 // checks not removed, scan order
let entered = [];                // per-slip bag/cash/coins typed so far (kept when the split changes)

async function load() {
  const [batch, all, deps, settings] = await Promise.all([api(apiUrl('batches', batchId)), api(apiUrl('checks', batchId)),
    api(apiUrl('deposits', '', `batch=${batchId}`)), api(apiUrl('info'))]);
  steps(4, batch);
  document.title = `Deposit slips · ${batchName(batch)} · ESP`;
  $('#batch-title').textContent = batchName(batch);
  checks = all.filter(c => !c.voided);
  const current = deps.filter(d => !d.superseded).sort((a, b) => a.slip_no - b.slip_no);
  const old = deps.filter(d => d.superseded);

  $('#not-final').hidden = batch.finalized && !batch.archived;
  $('#not-final').replaceChildren(...(batch.archived
    ? ['This batch was deleted. ', el('a', { href: pageUrl('batch', batchId) }, 'Restore it'), ' to continue.']
    : ['This batch isn\'t finalized yet — ', el('a', { href: pageUrl('finalize', batchId) }, 'finalize it first'), '.']));
  $('#current').hidden = !batch.finalized || batch.archived || !current.length;
  $('#prepare').hidden = !batch.finalized || batch.archived || current.length > 0;

  if (current.length) {
    const tot = current.reduce((s, d) => s + cents(d.total), 0);
    $('#current-info').textContent = `${current.length} slip(s) prepared ${when(current[0].created_at)} by ${current[0].created_by} · total ${money(tot / 100)}`;
    $('#slips').replaceChildren(...current.map(d => el('div', { class: 'slip-card' },
      el('h3', {}, `Slip ${d.slip_no} of ${d.n_in_set}`, el('span', { class: 'hint' }, `${d.bag_number ? `bag ${d.bag_number} · ` : ''}${d.n_checks} checks · ${money(d.total)}`)),
      el('a', { class: 'button primary', href: apiUrl('deposits', d.id, 'format=pdf'), target: '_blank', rel: 'noopener' }, 'Print ticket guide + check lists (PDF)'),
      slipView(d.id))));
  } else if (batch.finalized) {
    $('#program').textContent = batch.program_name;
    $('#treasurer').textContent = settings.treasurer_name;
    $('#prep-summary').textContent = `${checks.length} checks · ${money(batch.total)}`;
    renderPlan();
  }

  $('#old-panel').hidden = !old.length;
  $('#old-count').textContent = `(${old.length})`;
  $('#old').replaceChildren(...old.map(d => el('div', { class: 'slip-card' },
    el('h3', {}, `Set ${d.set_no} · slip ${d.slip_no} of ${d.n_in_set}`, el('span', { class: 'hint' }, `discarded ${when(d.superseded_at)}`)),
    slipView(d.id))));
}

// Split the checks (scan order) into slips of at most `max`.
function plan() {
  const max = parseInt($('#max').value, 10);
  const size = max > 0 ? max : checks.length;
  const out = [];
  for (let i = 0; i < checks.length; i += size) out.push(checks.slice(i, i + size));
  return out.length ? out : [[]];
}

function renderPlan() {
  const p = plan();
  $('#plan tbody').replaceChildren(...p.map((group, k) => {
    const e = (entered[k] ||= { bag: '', cash: '0', coins: '0' });
    const sum = group.reduce((s, c) => s + cents(c.amount), 0);
    const input = (key, attrs) => el('input', { value: e[key], 'data-k': k, 'data-key': key, size: 8, ...attrs,
      oninput: ev => { e[key] = ev.target.value; totals(); } });
    return el('tr', {},
      el('td', {}, `${k + 1} of ${p.length}`),
      el('td', {}, group.length ? `#${group[0].seq}–#${group[group.length - 1].seq} (${group.length})` : '—'),
      el('td', { class: 'num' }, money(sum / 100)),
      el('td', {}, input('bag', { placeholder: '(optional)' })),
      el('td', {}, input('cash', { inputmode: 'decimal' })),
      el('td', {}, input('coins', { inputmode: 'decimal' })),
      el('td', { class: 'num slip-total' }, ''));
  }));
  totals();
}

const amountOrZero = v => (String(v).trim() === '' || +v === 0 ? '0' : normAmount(v));

function totals() {
  const p = plan();
  let grand = 0;
  $$('#plan tbody tr').forEach((tr, k) => {
    const e = entered[k], g = p[k] || [];
    const t = g.reduce((s, c) => s + cents(c.amount), 0) + cents(amountOrZero(e.cash) || 0) + cents(amountOrZero(e.coins) || 0);
    grand += t;
    $('.slip-total', tr).textContent = money(t / 100);
  });
  $('#plan-total').textContent = `${p.length} slip(s) · total ${money(grand / 100)}`;
}

$('#max').addEventListener('input', renderPlan);

$('#create').addEventListener('click', async () => {
  const msg = $('#msg');
  const p = plan();
  const slips = p.map((g, k) => ({ n_checks: g.length, bag_number: entered[k].bag.trim(),
    cash: amountOrZero(entered[k].cash), coins: amountOrZero(entered[k].coins) }));
  if (slips.some(s => s.cash === null || s.coins === null)) return msg.replaceChildren(el('span', { class: 'bad' }, 'Currency/coins must be amounts like 120.00'));
  $('#create').disabled = true;
  try {
    await api(apiUrl('batches', batchId, 'op=slips'), { method: 'POST', json: { slips } });
    msg.textContent = '';
    await load();
  } catch (e) {
    msg.replaceChildren(el('span', { class: 'bad' }, e.message));
  } finally {
    $('#create').disabled = false;
  }
});

confirmClick($('#redo'), 'Click again: discard (void the paper tickets too)', async () => {
  try {
    await api(apiUrl('batches', batchId, 'op=discard'), { method: 'POST' });
    entered = [];
    await load();
  } catch (e) { $('#current-info').replaceChildren(el('span', { class: 'bad' }, e.message)); }
});

load().catch(e => { $('#batch-title').textContent = 'batch not found'; $('#msg').textContent = e.message; });
