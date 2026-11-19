import { api, $, el, header, steps, money, when, batchName, pageUrl, apiUrl } from './common.js';

header('index');
steps(1);

async function load() {
  const [batches, info] = await Promise.all([api(apiUrl('batches')), api(apiUrl('info'))]);
  const next = Math.max(0, ...batches.map(b => b.program_batch)) + 1;
  $('#preview').replaceChildren('This will be ', el('b', {}, `${info.program_name} · batch ${next}`),
    '. Batch numbers are assigned automatically.');

  const open = batches.filter(b => !b.done && !b.archived);
  $('#empty').hidden = open.length > 0;
  $('#batches tbody').replaceChildren(...open.map(b => {
    return el('tr', { class: 'clickable', onclick: () => (location.href = pageUrl('batch', b.id)) },
      el('td', {}, el('a', { href: pageUrl('batch', b.id) }, batchName(b))),
      el('td', { title: b.created_by }, when(b.created_at)),
      el('td', { class: 'num' }, String(b.n_live)),
      el('td', { class: 'num' + (b.n_need_amount ? ' needs' : '') }, b.n_need_amount ? String(b.n_need_amount) : '✓'),
      el('td', { class: 'num' }, money(b.total)),
      el('td', { class: 'hint' }, b.note));
  }));
}

$('#new-batch').addEventListener('submit', async e => {
  e.preventDefault();
  try {
    const { id } = await api(apiUrl('batches'), { method: 'POST', json: { note: $('#note').value.trim() } });
    location.href = pageUrl('batch', id);
  } catch (err) {
    $('#new-msg').replaceChildren(el('span', { class: 'bad' }, err.message));
  }
});
load();
