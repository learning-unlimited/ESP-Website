import { api, $, el, header, money, when, batchName, slipView, pageUrl, apiUrl } from './common.js';

header('history');

async function load() {
  const [allBatches, deposits] = await Promise.all([api(apiUrl('batches')), api(apiUrl('deposits'))]);
  const batches = allBatches.filter(b => !b.archived), archived = allBatches.filter(b => b.archived);
  $('#archived-panel').hidden = !archived.length;
  $('#archived tbody').replaceChildren(...archived.map(b => el('tr', {},
    el('td', {}, batchName(b)), el('td', {}, when(b.created_at)), el('td', {}, `${when(b.archived_at)} by ${b.archived_by}`),
    el('td', { class: 'num' }, String(b.n_checks)), el('td', { class: 'hint' }, b.note),
    el('td', {}, el('a', { href: pageUrl('batch', b.id) }, 'open'), ' ',
      el('button', { class: 'small', onclick: async () => { await api(apiUrl('batches', b.id, 'op=restore'), { method: 'POST' }); load(); } }, 'Restore')))));
  $('#no-batches').hidden = batches.length > 0;
  $('#batches tbody').replaceChildren(...batches.map(b => {
    const status = b.done ? `${b.n_slips} deposit slip(s)` : b.finalized ? 'finalized' : b.n_live ? 'open' : 'empty';
    return el('tr', {},
      el('td', {}, batchName(b)), el('td', {}, when(b.created_at)), el('td', {}, b.created_by),
      el('td', { class: 'num' }, String(b.n_live)), el('td', { class: 'num' }, String(b.n_checks - b.n_live)),
      el('td', { class: 'num' }, String(b.n_need_amount)), el('td', { class: 'num' }, money(b.total)),
      el('td', {}, status), el('td', { class: 'hint' }, b.note),
      el('td', {}, el('a', { href: pageUrl('batch', b.id) }, 'open')));
  }));
  $('#no-deposits').hidden = deposits.length > 0;
  $('#deposits tbody').replaceChildren(...deposits.flatMap(d => {
    // The sheet opens in a full-width row under the deposit.
    const sheetRow = el('tr', { class: 'sheet-row', hidden: true }, el('td', { colspan: 12 }));
    const toggle = el('button', { class: 'small', onclick: () => {
      if (!sheetRow.firstChild.firstChild) sheetRow.firstChild.append(slipView(d.id));
      sheetRow.hidden = !sheetRow.hidden;
      toggle.textContent = sheetRow.hidden ? 'View ▾' : 'Hide ▴';
    } }, 'View ▾');
    return [el('tr', { class: d.superseded ? 'superseded' : '' },
    el('td', { title: `created by ${d.created_by}` }, when(d.created_at)),
    el('td', {}, el('a', { href: pageUrl('slips', d.batch.id) }, batchName(d.batch))),
    el('td', {}, `${d.slip_no} of ${d.n_in_set}`, d.superseded ? el('span', { class: 'hint' }, ' (discarded)') : ''),
    el('td', {}, d.program_name), el('td', {}, d.treasurer_name), el('td', {}, d.bag_number || '—'),
    el('td', { class: 'num' }, String(d.n_checks)), el('td', { class: 'num' }, money(d.checks_total)),
    el('td', { class: 'num' }, money(d.cash)), el('td', { class: 'num' }, money(d.coins)), el('td', { class: 'num' }, money(d.total)),
    el('td', {}, toggle)), sheetRow];
  }));
}
load();
