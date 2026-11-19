import { api, $, el, header, steps, money, when, batchName, confirmClick, pageUrl, apiUrl } from './common.js';

const batchId = document.getElementById('checkscan').dataset.batchId || '';
if (!batchId) location.href = pageUrl('index');
header('index');
steps(3, { id: batchId });
$('#back').href = pageUrl('batch', batchId);
$('#next').href = pageUrl('slips', batchId);

async function load() {
  const [batch, all] = await Promise.all([api(apiUrl('batches', batchId)), api(apiUrl('checks', batchId))]);
  steps(3, batch);
  document.title = `Finalize · ${batchName(batch)} · ESP`;
  $('#batch-title').textContent = batchName(batch);
  const live = all.filter(c => !c.voided), voided = all.length - live.length;
  const needs = c => [c.amount == null && 'amount', !c.check_number && 'check #', !c.payee_ok && 'payee', !c.signed_ok && 'signature', !c.endorsed_ok && 'endorsement'].filter(Boolean);
  const missing = live.filter(c => needs(c).length);
  $('#summary').textContent = `${live.length} checks · total ${money(batch.total)}` + (voided ? ` · ${voided} removed (left out)` : '');
  $('#blocked').hidden = batch.finalized || (batch.ready && live.length > 0);
  $('#blocked').replaceChildren(live.length
    ? el('span', {}, el('b', {}, `Can't finalize yet: ${missing.length} check(s) still need an amount, check number, or a confirmation (payee, signature, endorsement) `),
        `(#${missing.map(c => c.seq).join(', #')}). `, el('a', { href: pageUrl('batch', batchId) }, 'Go back and fill them in'), '.')
    : el('span', {}, 'No checks in this batch yet — ', el('a', { href: pageUrl('batch', batchId) }, 'go back and scan some'), '.'));
  if (batch.archived) {
    $('#blocked').hidden = false;
    $('#blocked').replaceChildren('This batch was deleted. ', el('a', { href: pageUrl('batch', batchId) }, 'Restore it'), ' to continue.');
  }
  $('#finalize').hidden = batch.finalized || batch.archived; $('#finalize').disabled = !batch.ready;
  $('#reopen').hidden = !batch.finalized || batch.archived; $('#reopen').disabled = batch.done;
  $('#reopen').title = batch.done ? 'Discard the deposit slips on step 4 first, then reopen the batch for edits' : '';
  $('#next').hidden = !batch.finalized;
  $('#explain').hidden = batch.finalized;
  $('#status').replaceChildren(batch.finalized
    ? el('p', { class: 'ok' }, `Finalized ${when(batch.finalized_at)} by ${batch.finalized_by}.`,
        batch.done ? el('span', { class: 'hint' }, ' If an error is found, discard the deposit slips (step 4), then reopen the batch for edits here.') : '')
    : '');
  $('#checks tbody').replaceChildren(...all.map(c => {
    const m = c.voided ? [] : needs(c);
    const yes = v => (c.voided ? '' : v ? '✓' : '✗');
    return el('tr', { class: c.voided ? 'voided' : m.length ? 'missing' : '' },
      el('td', {}, String(c.seq)), el('td', {}, c.check_number || 'missing'),
      el('td', { class: 'num' }, c.amount == null ? (c.voided ? '—' : 'missing') : money(c.amount)),
      el('td', {}, yes(c.payee_ok)), el('td', {}, yes(c.signed_ok)), el('td', {}, yes(c.endorsed_ok)),
      el('td', { class: 'hint' }, c.voided ? 'removed' : m.length ? 'needs ' + m.join(', ') : ''));
  }));
}

function fail(e) { $('#msg').replaceChildren(el('span', { class: 'bad' }, e.message)); }
confirmClick($('#finalize'), 'Click again to finalize', async () => {
  try { await api(apiUrl('batches', batchId, 'op=finalize'), { method: 'POST' }); $('#msg').textContent = ''; await load(); } catch (e) { fail(e); }
});
confirmClick($('#reopen'), 'Click again to reopen', async () => {
  try { await api(apiUrl('batches', batchId, 'op=reopen'), { method: 'POST' }); location.href = pageUrl('batch', batchId); } catch (e) { fail(e); }
});
load().catch(e => { $('#batch-title').textContent = 'batch not found'; fail(e); });
