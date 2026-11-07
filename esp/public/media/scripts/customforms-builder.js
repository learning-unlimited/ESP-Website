/*
 * Custom form builder.
 *
 * The form is held as one state object (form -> pages -> sections -> fields) and the
 * page is re-rendered from it after every change, which also gives undo/redo.
 * Forms are loaded from /customforms/metadata/ and saved to /customforms/submit/ or
 * /customforms/modify/ in the same JSON format the server has always accepted, so
 * existing forms and their responses keep working.
 */
(function () {
"use strict";

const CONFIG = JSON.parse(document.getElementById('cfb-config').textContent);
const URLS = {
    landing: '/customforms/', buildData: '/customforms/builddata/', metadata: '/customforms/metadata/',
    submit: '/customforms/submit/', modify: '/customforms/modify/', perms: '/customforms/getperms/',
    links: '/customforms/getlinks/', modules: '/customforms/getmodules/',
};

// ---------- Question types ----------
//   cap: the response column's character limit; correct: how a correct answer is entered
const TYPES = {
    textField:     { label: 'Short answer', code: 'Aa', group: 'Text', text: true, cap: 30, correct: 'text' },
    longTextField: { label: 'One-line answer', code: 'Aa+', group: 'Text', text: true, cap: 60, correct: 'text' },
    longAns:       { label: 'Paragraph', code: '¶', group: 'Text', text: true, correct: 'textarea' },
    reallyLongAns: { label: 'Long paragraph', code: '¶¶', group: 'Text', text: true, correct: 'textarea' },
    radio:         { label: 'Multiple choice', code: '◉', group: 'Choice', options: true, optCap: 200, correct: 'one' },
    dropdown:      { label: 'Dropdown', code: '▾', group: 'Choice', options: true, optCap: 200, correct: 'one' },
    checkboxes:    { label: 'Checkboxes', code: '☑', group: 'Choice', options: true, multi: true, correct: 'many' },
    multiselect:   { label: 'Multi-select list', code: '≣', group: 'Choice', options: true, multi: true, correct: 'many' },
    radio_yesno:   { label: 'Yes / No', code: 'Y/N', group: 'Choice', correct: 'yesno' },
    null_boolean:  { label: 'Yes / No / Unknown', code: 'Y/N?', group: 'Choice', correct: 'nullbool' },
    boolean:       { label: 'Single checkbox', code: '✓', group: 'Choice' },
    numeric:       { label: 'Whole number', code: '#', group: 'Number & date', correct: 'number' },
    date:          { label: 'Date', code: 'DT', group: 'Number & date', correct: 'date' },
    time:          { label: 'Time', code: 'TM', group: 'Number & date', correct: 'time' },
    email:         { label: 'Email', code: '@', group: 'Contact & identity', defaultLabel: 'Your email' },
    phone:         { label: 'Phone', code: 'PH', group: 'Contact & identity', defaultLabel: 'Your phone number' },
    state:         { label: 'US state', code: 'ST', group: 'Contact & identity', defaultLabel: 'Your state' },
    gender:        { label: 'Gender', code: 'GN', group: 'Contact & identity', defaultLabel: 'Your gender' },
    pronoun:       { label: 'Pronouns', code: 'PR', group: 'Contact & identity', defaultLabel: 'Your pronouns' },
    file:          { label: 'File upload', code: 'UP', group: 'Files & layout' },
    instructions:  { label: 'Instructions block', code: 'i', group: 'Files & layout', layout: true },
};
const GROUPS = ['Text', 'Choice', 'Number & date', 'Contact & identity', 'Files & layout'];
//   Type changes that the response table can make without losing saved answers
const SAFE_CHANGES = {
    textField: ['longTextField', 'longAns', 'reallyLongAns'], longTextField: ['longAns', 'reallyLongAns'],
    longAns: ['reallyLongAns'], reallyLongAns: ['longAns'],
    radio: ['dropdown'], dropdown: ['radio'], checkboxes: ['multiselect'], multiselect: ['checkboxes'],
};
const MODULE_NAMES = {
    StudentCustomFormModule: 'Student registration: custom form',
    TeacherCustomFormModule: 'Teacher registration: custom form',
    TeacherQuizModule: 'Teacher registration: logistics quiz',
};
const ROLE_NAMES = { Teacher: 'Teachers', Student: 'Students' };
const LIMITS = { title: 40, sectionTitle: 40, sectionDesc: 140, label: 200, successMessage: 500, successUrl: 200, perms: 200 };
let LINK_MODELS = [];

function registerLinkTypes(data) {
    LINK_MODELS = data.only_fkey_models || [];
    Object.entries(data.link_fields || {}).forEach(([category, fields]) => {
        const group = 'Profile: ' + categoryName(category);
        GROUPS.push(group);
        Object.entries(fields).forEach(([key, info]) => {
            TYPES[key] = { label: info.disp_name, code: initials(info.disp_name), group, linked: true, category,
                ques: info.ques || info.disp_name, modelRequired: !!info.required };
        });
    });
}
function categoryName(category) {
    return { ContactInfo: 'contact info', TeacherInfo: 'teacher info' }[category] || category.replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase();
}
function initials(text) { return text.split(/[\s/]+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join(''); }
function typeInfo(type) {
    //   Types the builder doesn't know (e.g. from older versions) are kept as they are
    if (!TYPES[type]) TYPES[type] = { label: type, code: '?', group: null, unknown: true };
    return TYPES[type];
}

// ---------- Helpers ----------
const uid = () => Math.random().toString(36).slice(2, 9);
const INT = /^-?\d+$/;
const NONNEG_INT = /^\d+$/;
const blank = v => v === undefined || v === null || String(v).trim() === '';
const plural = (n, word) => n + ' ' + word + (n === 1 ? '' : 's');
const isNone = linkType => !linkType || linkType === '-1';

function h(tag, attrs, ...kids) {
    //   Builds an element; user text only ever goes in as text, never as HTML
    const el = document.createElement(tag);
    for (const k in (attrs || {})) {
        const v = attrs[k];
        if (v === false || v === null || v === undefined) continue;
        if (k === 'class') el.className = v;
        else if (k === 'text') el.textContent = v;
        else if (k === 'icon') el.innerHTML = ICON[v];
        else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
        else if (k in el && typeof v !== 'string') el[k] = v;
        else el.setAttribute(k, v === true ? '' : v);
    }
    kids.flat().forEach(c => { if (c !== null && c !== undefined && c !== false) el.append(c.nodeType ? c : document.createTextNode(String(c))); });
    return el;
}
const ICON = {
    up: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m6 15 6-6 6 6"/></svg>',
    down: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>',
    copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8"/></svg>',
    trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg>',
    grip: '<svg viewBox="0 0 10 16" fill="currentColor" aria-hidden="true"><circle cx="2" cy="2" r="1.5"/><circle cx="8" cy="2" r="1.5"/><circle cx="2" cy="8" r="1.5"/><circle cx="8" cy="8" r="1.5"/><circle cx="2" cy="14" r="1.5"/><circle cx="8" cy="14" r="1.5"/></svg>',
    x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
};
const iconBtn = (name, label, onclick, cls) => h('button', { class: cls || '', type: 'button', 'aria-label': label, title: label, onclick, icon: name });

// ---------- Server ----------
function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-cookie-name"]');
    const name = (meta && meta.getAttribute('content')) || 'csrftoken';
    const cookie = document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith(name + '='));
    return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : '';
}
function serverMessage(res, data) {
    if (data && typeof data.message === 'string' && data.message) return data.message;
    if (data && typeof data.error === 'string' && data.error) return data.error;
    if (res.redirected && /login/.test(res.url)) return 'Your session has expired. Log in again in another tab, then try again.';
    if (res.status === 403) return 'The server refused the request (403). Your session may have expired: log in again in another tab, then try again.';
    return 'The server returned an error (' + res.status + ').';
}
async function request(url, opts) {
    const res = await fetch(url, Object.assign({ credentials: 'same-origin' }, opts, {
        headers: Object.assign({ 'X-Requested-With': 'XMLHttpRequest' }, (opts || {}).headers) }));
    const text = await res.text();
    let data = null;
    try { data = JSON.parse(text); } catch (e) { data = null; }
    return { res, text, data };
}
async function getJSON(url, params) {
    const u = new URL(url, window.location.origin);
    Object.entries(params || {}).forEach(([k, v]) => u.searchParams.set(k, v));
    let r;
    try { r = await request(u.toString()); } catch (e) { throw new Error('Could not reach the server. Check your connection and try again.'); }
    if (!r.res.ok || r.data === null || r.res.redirected) throw new Error(serverMessage(r.res, r.data));
    return r.data;
}

//   Lists fetched on demand (program groups, link targets, registration modules), cached per key
const remote = { perms: {}, links: {}, modules: {} };
function fetchList(kind, key, url, params) {
    const cache = remote[kind];
    if (!cache[key]) {
        cache[key] = { status: 'loading' };
        getJSON(url, params).then(data => { cache[key] = { status: 'ok', data }; })
            .catch(e => { cache[key] = { status: 'error', error: e.message }; })
            .then(() => render({ keepFocus: true }));
    }
    return cache[key];
}
const permGroups = prog => fetchList('perms', prog, URLS.perms, { prog_id: prog });
const linkTargets = model => fetchList('links', model, URLS.links, { link_model: model });
const programModules = prog => fetchList('modules', prog, URLS.modules, { program: prog });

// ---------- State ----------
const meta = { formId: null, savedLinkType: null, loaded: false, fatal: false };
let state, sel = { kind: 'form' }, pageIx = 0, mode = 'edit', saving = false, savedJSON = null;
let hist = [], fut = [], lastKey = null, lastT = 0, problemIx = 0;
let pv = { step: 0, answers: {}, errors: {}, done: false };

const blankSection = () => ({ id: uid(), serverId: null, title: '', description: '', fields: [] });
const blankPage = () => ({ id: uid(), serverId: null, sections: [blankSection()] });
function blankState() {
    return { title: '', description: '', pages: [blankPage()],
        settings: { anonymous: false, successMessage: '', successUrl: '', role: '', permProgram: '', permList: '', permExtra: [],
            linkType: '-1', linkId: -1, linkModule: '' } };
}
function newField(type) {
    const t = TYPES[type];
    const f = { id: uid(), serverId: null, savedType: null, type, label: t.defaultLabel || '', help: '', required: false, extra: {} };
    if (t.options) f.options = ['Option 1', 'Option 2'];
    if (t.text) { f.charMin = ''; f.charMax = ''; }
    if (type === 'numeric') { f.min = ''; f.max = ''; }
    if (t.linked) { f.label = t.ques; f.required = t.modelRequired; f.linkId = '-1'; }
    return f;
}

function splitPair(value) {
    const parts = String(value || '').split(',');
    return [(parts[0] || '').trim(), (parts[1] || '').trim()];
}
function correctFromServer(t, value) {
    if (blank(value)) return null;
    if (t.correct === 'one') { const n = Number(value); return Number.isInteger(n) ? n : null; }
    if (t.correct === 'many') return String(value).split('|').map(Number).filter(Number.isInteger);
    if (t.correct === 'date') return String(value).slice(0, 10);
    return String(value);
}
function fieldFromServer(fd, asCopy) {
    const t = typeInfo(fd.field_type);
    const attrs = {};
    //   Fields without attributes come back as {null: null}
    Object.entries(fd.attributes || {}).forEach(([k, v]) => { if (k !== 'null' && v !== null) attrs[k] = v; });
    const f = { id: uid(), serverId: asCopy ? null : fd.id, savedType: asCopy ? null : fd.field_type, type: fd.field_type,
        label: fd.label || '', help: fd.help_text || '', required: !!fd.required, extra: {} };
    if (t.options) { f.options = 'options' in attrs ? String(attrs.options).split('|') : []; delete attrs.options; }
    if (fd.field_type === 'radio_yesno') delete attrs.options;
    if (t.text) { [f.charMin, f.charMax] = splitPair(attrs.charlimits); delete attrs.charlimits; }
    if (fd.field_type === 'numeric') { [f.min, f.max] = splitPair(attrs.limits); delete attrs.limits; }
    if (t.correct && 'correct_answer' in attrs) { f.correct = correctFromServer(t, attrs.correct_answer); delete attrs.correct_answer; }
    if (t.linked) { f.linkId = blank(attrs.link_id) ? '-1' : String(attrs.link_id); delete attrs.link_id; }
    f.extra = attrs;
    return f;
}
function fromMetadata(md, asCopy) {
    const st = blankState(), s = st.settings;
    st.title = asCopy ? ('Copy of ' + (md.title || '')).slice(0, LIMITS.title) : (md.title || '');
    st.description = md.desc || '';
    s.anonymous = !!md.anonymous;
    s.successMessage = md.success_message || '';
    s.successUrl = md.success_url || '';
    const perms = (md.perms || '').replace(/^,+|,+$/g, '').split(',');
    if (perms[0]) {
        s.role = perms[0]; s.permProgram = perms[1] || ''; s.permList = perms[2] || ''; s.permExtra = perms.slice(3);
    }
    s.linkType = md.link_type || '-1';
    s.linkId = isNone(s.linkType) ? -1 : Number(md.link_id);
    s.linkModule = md.link_module || '';
    st.pages = (md.pages || []).map(page => ({ id: uid(), serverId: asCopy ? null : page[0][0].section__page__id,
        sections: page.map(section => ({ id: uid(), serverId: asCopy ? null : section[0].section__id,
            title: section[0].section__title || '', description: section[0].section__description || '',
            fields: section.map(fd => fieldFromServer(fd, asCopy)) })) }));
    if (!st.pages.length) st.pages.push(blankPage());
    return st;
}

function commit(mutate, opts) {
    opts = opts || {};
    const now = Date.now();
    //   Typing into one box within 1.5s counts as one change for undo
    if (!(opts.key && opts.key === lastKey && now - lastT < 1500)) {
        hist.push(snapshot()); if (hist.length > 100) hist.shift();
    }
    lastKey = opts.key || null; lastT = now; fut = [];
    mutate(state);
    render({ inspector: !opts.keepInspector });
}
//   Each history entry also records the page and selection, so undo/redo return to where the change was made
function snapshot() { return { state: JSON.stringify(state), pageIx, sel: Object.assign({}, sel) }; }
function restore(snap) {
    state = JSON.parse(snap.state); pageIx = Math.min(snap.pageIx, state.pages.length - 1); sel = snap.sel;
    const loc = sel.id ? find(sel.id) : null;
    if (sel.id && !loc) sel = { kind: 'form' }; else if (loc) pageIx = loc.pi;
    lastKey = null; render();
}
function undo() { if (!hist.length || saving) return; fut.push(snapshot()); restore(hist.pop()); toast('Undone'); }
function redo() { if (!fut.length || saving) return; hist.push(snapshot()); restore(fut.pop()); toast('Redone'); }

function find(id) {
    for (let pi = 0; pi < state.pages.length; pi++) {
        const p = state.pages[pi];
        for (let si = 0; si < p.sections.length; si++) {
            const s = p.sections[si];
            if (s.id === id) return { kind: 'section', page: p, pi, section: s, si };
            for (let fi = 0; fi < s.fields.length; fi++) if (s.fields[fi].id === id) return { kind: 'field', page: p, pi, section: s, si, field: s.fields[fi], fi };
        }
    }
    return null;
}
const canDeleteSection = () => state.pages.length > 1 || state.pages[0].sections.length > 1;
const allFields = () => state.pages.flatMap(p => p.sections.flatMap(s => s.fields));
const hasLinked = () => allFields().some(f => TYPES[f.type].linked);
const isQuiz = () => state.settings.linkModule === 'TeacherQuizModule' && linkModuleApplies();
const linkModuleApplies = () => state.settings.linkType === 'Program' && state.settings.linkId !== -1;
const hasCorrect = f => f.correct !== undefined && f.correct !== null && f.correct !== '' && !(Array.isArray(f.correct) && !f.correct.length);
const isCorrect = (f, i) => Array.isArray(f.correct) ? f.correct.includes(i) : f.correct === i;
const savedAnswersNote = n => meta.formId && n ? ' Saved answers to ' + (n === 1 ? 'it' : 'them') + ' are deleted when you save.' : '';
const savedCount = fields => fields.filter(f => f.serverId).length;
//   Compares what would be sent to the server, so selection and other view state never count as changes
const dirty = () => !!state && JSON.stringify(toServer()) !== savedJSON;
function markSaved() { savedJSON = JSON.stringify(toServer()); }

// ---------- Validation (what blocks saving) ----------
function fieldProblems(f) {
    const t = TYPES[f.type], out = [];
    if (t.layout) { if (blank(f.label) && blank(f.help)) out.push('Instructions need a heading or some text.'); }
    else if (blank(f.label)) out.push('Questions need a label.');
    if (f.label.length > LIMITS.label) out.push('The label is longer than ' + LIMITS.label + ' characters.');
    if (t.options) {
        if (!f.options.length) out.push('Add at least one choice.');
        if (f.options.some(o => !o.trim())) out.push('A choice is empty.');
        if (f.options.some(o => o.includes('|'))) out.push('Choices can’t contain the | character.');
        if (new Set(f.options.map(o => o.trim())).size !== f.options.length) out.push('Two choices are the same.');
        if (t.optCap && f.options.some(o => o.length > t.optCap)) out.push('Choices can be at most ' + t.optCap + ' characters.');
    }
    if (t.text) {
        if (!blank(f.charMin) && !NONNEG_INT.test(f.charMin)) out.push('The minimum length must be a whole number.');
        if (!blank(f.charMax) && !NONNEG_INT.test(f.charMax)) out.push('The maximum length must be a whole number.');
        else if (!blank(f.charMax) && Number(f.charMax) < 1) out.push('The maximum length must be at least 1.');
        else if (t.cap && Number(f.charMax) > t.cap) out.push('Answers to this type can be at most ' + t.cap + ' characters.');
        if (NONNEG_INT.test(f.charMin) && NONNEG_INT.test(f.charMax) && Number(f.charMin) > Number(f.charMax)) out.push('The minimum length is longer than the maximum.');
    }
    if (f.type === 'numeric') {
        if (!blank(f.min) && !INT.test(f.min)) out.push('The smallest value must be a whole number.');
        if (!blank(f.max) && !INT.test(f.max)) out.push('The largest value must be a whole number.');
        if (INT.test(f.min) && INT.test(f.max) && Number(f.min) > Number(f.max)) out.push('The smallest value is larger than the largest.');
    }
    if (hasCorrect(f)) {
        if (t.correct === 'one' && !(f.correct >= 0 && f.correct < f.options.length)) out.push('The correct answer is no longer one of the choices.');
        if (t.correct === 'many' && f.correct.some(i => !(i >= 0 && i < f.options.length))) out.push('A correct answer is no longer one of the choices.');
        if (t.correct === 'number' && !Number.isFinite(Number(f.correct))) out.push('The correct answer must be a number.');
        if (t.correct === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(f.correct)) out.push('The correct answer must be a date.');
        if (t.correct === 'time' && !/^([01]\d|2[0-3]):[0-5]\d$/.test(f.correct)) out.push('The correct answer must be a time like 09:30 or 14:00.');
    }
    if (t.linked && f.linkId === '') out.push('Choose which record this question updates.');
    else if (t.linked && f.linkId !== '-1') {
        const list = remote.links[t.category];
        if (list && list.status === 'ok' && !list.data.some(o => String(o.id) === f.linkId)) out.push('The chosen record no longer exists.');
    }
    return out;
}
function formProblems() {
    const s = state.settings, out = [];
    if (!state.title.trim()) out.push({ msg: 'The form needs a title.', id: null });
    if (state.title.trim().length > LIMITS.title) out.push({ msg: 'The title is longer than ' + LIMITS.title + ' characters.', id: null });
    if (s.successMessage.length > LIMITS.successMessage) out.push({ msg: 'The thank-you message is longer than ' + LIMITS.successMessage + ' characters.', id: null });
    const u = s.successUrl.trim();
    if (u && !/^(https?:\/\/|\/)/i.test(u)) out.push({ msg: 'The redirect address must start with /, http:// or https://.', id: null });
    if (u.length > LIMITS.successUrl) out.push({ msg: 'The redirect address is longer than ' + LIMITS.successUrl + ' characters.', id: null });
    if (s.anonymous && hasLinked()) out.push({ msg: 'Anonymous forms can’t use profile questions.', id: null });
    if (s.role && s.permProgram) {
        const groups = remote.perms[s.permProgram];
        if (!s.permList) out.push({ msg: 'Pick which group in the program can fill in the form, or set the program to “Any”.', id: null });
        else if (groups && groups.status === 'ok' && !(groupsFor(groups.data, s.role) || []).some(([k]) => k === s.permList)) out.push({ msg: 'The chosen group is no longer available for this program.', id: null });
    }
    if (permsString().length > LIMITS.perms) out.push({ msg: 'The access settings are too long to save.', id: null });
    if (!isNone(s.linkType) && s.linkId !== -1) {
        const list = remote.links[s.linkType];
        if (list && list.status === 'ok' && !list.data.some(o => o.id === s.linkId)) out.push({ msg: 'The linked ' + s.linkType.toLowerCase() + ' no longer exists.', id: null });
    }
    allFields().forEach(f => fieldProblems(f).forEach(m => out.push({ msg: m, id: f.id })));
    state.pages.forEach((p, pi) => p.sections.forEach(sec => {
        const name = (sec.title.trim() ? 'The section “' + sec.title.trim() + '”' : 'An untitled section') + ' on page ' + (pi + 1);
        if (!sec.fields.length) out.push({ id: sec.id, msg: name + ' has no questions.' });
        if (sec.title.length > LIMITS.sectionTitle) out.push({ id: sec.id, msg: name + ' has a heading longer than ' + LIMITS.sectionTitle + ' characters.' });
        if (sec.description.length > LIMITS.sectionDesc) out.push({ id: sec.id, msg: name + ' has a description longer than ' + LIMITS.sectionDesc + ' characters.' });
    }));
    return out;
}

// ---------- What gets saved ----------
function groupsFor(perms, role) { return { Teacher: perms.teachers, Student: perms.students }[role] || null; }
function permsString() {
    const s = state.settings;
    if (!s.role) return '';
    const parts = [s.role];
    if (s.permProgram) { parts.push(s.permProgram); if (s.permList) parts.push(s.permList, ...s.permExtra); }
    return parts.join(',');
}
function correctToServer(f) {
    const t = TYPES[f.type];
    if (!t.correct || !hasCorrect(f)) return null;
    if (t.correct === 'one') return String(f.correct);
    if (t.correct === 'many') return [...f.correct].sort((a, b) => a - b).join('|');
    return String(f.correct);
}
function fieldAttrs(f) {
    const t = TYPES[f.type], a = Object.assign({}, f.extra);
    if (t.linked) { a.link_id = f.linkId || '-1'; return a; }
    if (t.options) a.options = f.options.join('|');
    if (f.type === 'radio_yesno') a.options = 'Yes|No';
    //   A blank maximum still has to respect the response column's limit
    if (t.text) a.charlimits = f.charMin.trim() + ',' + (f.charMax.trim() || (t.cap ? String(t.cap) : ''));
    if (f.type === 'numeric') a.limits = f.min.trim() + ',' + f.max.trim();
    const c = correctToServer(f);
    if (c !== null) a.correct_answer = c;
    return a;
}
function toServer() {
    const s = state.settings;
    const out = { title: state.title.trim(), desc: state.description, anonymous: s.anonymous,
        success_message: s.successMessage, success_url: s.successUrl.trim(), perms: permsString(),
        link_type: s.linkType, link_id: isNone(s.linkType) ? -1 : s.linkId, pages: [] };
    if (linkModuleApplies() && s.linkModule) {
        out.link_module = s.linkModule;
        out.link_tl = s.linkModule === 'StudentCustomFormModule' ? 'learn' : 'teach';
    }
    if (meta.formId) out.form_id = meta.formId;
    state.pages.forEach((p, pi) => out.pages.push({ parent_id: p.serverId || -1, seq: pi,
        sections: p.sections.map((sec, si) => ({
            data: { question_text: sec.title.trim(), help_text: sec.description.trim(), field_type: 'section', seq: si, parent_id: sec.serverId || -1, attrs: {} },
            fields: sec.fields.map((f, fi) => ({ data: { question_text: f.label.trim(), help_text: f.help.trim(), field_type: f.type,
                required: !!f.required && !TYPES[f.type].layout, seq: fi, parent_id: f.serverId || -1, attrs: fieldAttrs(f) } })) })) }));
    return out;
}

// ---------- Render ----------
function render(opts) {
    opts = opts || {};
    if (!state) return;
    pageIx = Math.min(Math.max(0, pageIx), state.pages.length - 1);
    //   Re-rendering replaces the inspector's inputs, so put the cursor back where it was
    const active = opts.keepFocus && document.activeElement && document.activeElement.id ? document.activeElement : null;
    const caret = active && 'selectionStart' in active ? [active.selectionStart, active.selectionEnd] : null;
    renderTop(); renderPalette();
    if (mode === 'edit') renderCanvas(); else renderPreview();
    if (opts.inspector !== false) renderInspector();
    if (active && !document.body.contains(active)) {
        const again = document.getElementById(active.id);
        if (again) { again.focus({ preventScroll: true }); if (caret) try { again.setSelectionRange(caret[0], caret[1]); } catch (e) { /* not a text input */ } }
    }
}

function renderTop() {
    const t = document.getElementById('cfb-title');
    if (document.activeElement !== t) t.value = state.title;
    document.getElementById('cfb-crumb').textContent = meta.formId ? 'Editing form #' + meta.formId : 'New form';
    const st = document.getElementById('cfb-status'); st.replaceChildren();
    const probs = formProblems();
    const changed = dirty();
    st.className = 'cfb-status' + (changed ? ' cfb-dirty' : '');
    st.append(h('span', { class: 'cfb-dot', 'aria-hidden': 'true' }),
        saving ? 'Saving…' : changed ? 'Unsaved changes' : meta.formId ? 'No unsaved changes' : 'Not saved yet');
    if (probs.length) st.append(' · ', h('button', { type: 'button', title: 'Go to the next problem', text: plural(probs.length, 'problem'), onclick: () => goToProblem(probs) }));
    document.getElementById('cfb-undo').disabled = !hist.length || saving;
    document.getElementById('cfb-redo').disabled = !fut.length || saving;
    const save = document.getElementById('cfb-save');
    save.textContent = saving ? 'Saving…' : meta.formId ? 'Save changes' : 'Create form';
    save.disabled = saving || meta.fatal || probs.length > 0 || (meta.formId && !changed);
    save.title = probs.length ? 'Fix the problems first' : '';
    document.getElementById('cfb-m-edit').setAttribute('aria-pressed', mode === 'edit');
    document.getElementById('cfb-m-preview').setAttribute('aria-pressed', mode === 'preview');
    document.getElementById('cfb-panes').classList.toggle('cfb-previewing', mode === 'preview');
    document.getElementById('cfb-settings').setAttribute('aria-pressed', mode === 'edit' && sel.kind === 'form');
}
function goToProblem(probs) {
    const p = probs[problemIx++ % probs.length];
    mode = 'edit';
    if (p.id) { const loc = find(p.id); pageIx = loc.pi; sel = { kind: loc.kind, id: p.id }; } else sel = { kind: 'form' };
    render();
    requestAnimationFrame(() => {
        const el = document.querySelector('.cfb-field.cfb-sel, .cfb-section.cfb-selected-ring, .cfb-formhead');
        if (el) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
        if (!p.id) toast(p.msg);
    });
}

function renderPalette() {
    const root = document.getElementById('cfb-palette'); root.replaceChildren();
    const anon = state.settings.anonymous;
    GROUPS.forEach(g => {
        const tiles = h('div', { class: 'cfb-tiles' });
        Object.entries(TYPES).filter(([, t]) => t.group === g).forEach(([key, t]) => {
            const disabled = mode !== 'edit' || (t.linked && anon);
            tiles.append(h('button', { type: 'button', class: 'cfb-tile' + (t.linked ? ' cfb-linked' : ''), draggable: !disabled, disabled,
                title: t.linked && anon ? 'Anonymous forms can’t use profile questions' : 'Click to add, or drag onto the page',
                ondragstart: e => { e.dataTransfer.setData('text/x-cfb-type', key); e.dataTransfer.effectAllowed = 'copy'; },
                onclick: () => addField(key) }, h('span', { class: 'cfb-code', text: t.code }), t.label));
        });
        const linkedGroup = g.startsWith('Profile: ');
        root.append(h('div', { class: 'cfb-group' }, h('h3', {}, g, linkedGroup ? h('span', { text: 'saved to profile' }) : null), tiles,
            linkedGroup ? h('p', { class: 'cfb-hint', text: anon ? 'Turn off “Anonymous” in the form settings to use these.' : 'Pre-filled from the respondent’s profile; their answer updates it.' }) : null));
    });
}

function addField(type, target) {
    if (mode !== 'edit') return;
    const nf = newField(type);
    commit(s => {
        let sec, at;
        if (target) { sec = s.pages[target.pi].sections[target.si]; at = target.at; } else {
            const loc = sel.id ? find(sel.id) : null;
            if (loc && loc.pi === pageIx) { sec = loc.page.sections[loc.si]; at = loc.kind === 'field' ? loc.fi + 1 : sec.fields.length; } else {
                const p = s.pages[pageIx]; sec = p.sections[p.sections.length - 1]; at = sec.fields.length;
            }
        }
        sec.fields.splice(at, 0, nf);
    });
    sel = { kind: 'field', id: nf.id }; render();
    requestAnimationFrame(() => {
        const el = document.querySelector('[data-id="' + nf.id + '"]'); if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        const inp = document.getElementById('cfb-i-label'); if (inp) inp.focus();
    });
}

function renderCanvas() {
    const root = document.getElementById('cfb-canvas'); root.replaceChildren();
    const tabs = h('div', { class: 'cfb-pages', role: 'tablist', 'aria-label': 'Pages' });
    state.pages.forEach((p, i) => {
        const count = p.sections.reduce((n, s) => n + s.fields.length, 0);
        tabs.append(h('button', { type: 'button', class: 'cfb-pagetab', role: 'tab', 'aria-selected': i === pageIx ? 'true' : 'false',
            onclick: () => { pageIx = i; render({ inspector: false }); },
            ondragover: e => { if (e.dataTransfer.types.includes('text/x-cfb-field')) e.preventDefault(); },
            ondrop: e => { const id = e.dataTransfer.getData('text/x-cfb-field'); if (id) { e.preventDefault(); moveFieldToPage(id, i); } } },
            'Page ' + (i + 1), h('span', { class: 'cfb-n', text: count })));
    });
    tabs.append(h('button', { type: 'button', class: 'cfb-pagetab cfb-addpage', onclick: () => {
        const np = blankPage();
        commit(s => s.pages.push(np)); pageIx = state.pages.length - 1; sel = { kind: 'section', id: np.sections[0].id }; render();
    } }, '+ Add page'));
    root.append(tabs);

    const sheet = h('div', { class: 'cfb-sheet' });
    if (pageIx === 0) {
        const s = state.settings;
        const openSettings = () => { sel = { kind: 'form' }; render(); };
        sheet.append(h('div', { class: 'cfb-formhead' + (sel.kind === 'form' ? ' cfb-selected-ring' : ''), tabindex: 0, role: 'button', 'aria-label': 'Form settings', title: 'Edit form settings',
            onclick: openSettings, onkeydown: e => { if (e.key === 'Enter') openSettings(); } },
            state.title.trim() ? h('h1', { text: state.title }) : h('h1', { class: 'cfb-untitled', text: 'Untitled form' }),
            state.description ? h('p', { text: state.description }) : null,
            h('div', { class: 'cfb-meta' },
                h('span', { class: 'cfb-pill cfb-accent', text: linkSentence(true) }),
                h('span', { class: 'cfb-pill', text: audienceSentence(true) }),
                s.anonymous ? h('span', { class: 'cfb-pill cfb-warn', text: 'Anonymous' }) : null,
                meta.formId ? h('span', { class: 'cfb-pill', text: 'Form #' + meta.formId }) : null)));
    }
    const page = state.pages[pageIx];
    page.sections.forEach((sec, si) => sheet.append(renderSection(sec, si)));
    sheet.append(h('button', { type: 'button', class: 'cfb-btn cfb-add-section', onclick: () => {
        const ns = blankSection();
        commit(s => s.pages[pageIx].sections.push(ns)); sel = { kind: 'section', id: ns.id }; render();
    } }, '+ Add section'));
    if (state.pages.length > 1) sheet.append(h('button', { type: 'button', class: 'cfb-linkbtn cfb-danger-text', onclick: () => deletePage(pageIx) }, 'Delete this page'));
    root.append(sheet);
}

function renderSection(sec, si) {
    const isSel = sel.kind === 'section' && sel.id === sec.id;
    const list = h('div', { class: 'cfb-fields' });
    if (!sec.fields.length) list.append(h('div', { class: 'cfb-empty-drop', text: 'Drag a question here, or pick one from the list.' }),
        h('p', { class: 'cfb-problem', style: 'margin:0 4px', text: canDeleteSection() ? 'Add a question to this section, or delete it.' : 'Add a question to this section.' }));
    sec.fields.forEach((f, fi) => list.append(renderField(f, fi)));
    wireDrop(list, si);
    const select = () => { sel = { kind: 'section', id: sec.id }; render(); };
    return h('section', { class: 'cfb-section' + (isSel ? ' cfb-selected-ring' : '') },
        h('div', { class: 'cfb-section-head', tabindex: 0, role: 'button', 'aria-label': 'Section settings',
            onclick: select, onkeydown: e => { if (e.key === 'Enter' && e.target === e.currentTarget) select(); } },
            h('div', {}, sec.title.trim() ? h('h2', { text: sec.title }) : h('h2', { class: 'cfb-untitled', text: 'Untitled section' }), sec.description ? h('p', { text: sec.description }) : null),
            iconBtn('trash', 'Delete section', e => { e.stopPropagation(); deleteSection(sec.id); }, 'cfb-linkbtn')),
        list,
        h('div', { class: 'cfb-section-foot' },
            h('button', { type: 'button', class: 'cfb-linkbtn', onclick: () => { sel = { kind: 'section', id: sec.id }; addField('textField'); } }, '+ Short answer'),
            h('button', { type: 'button', class: 'cfb-linkbtn', onclick: () => { sel = { kind: 'section', id: sec.id }; addField('radio'); } }, '+ Multiple choice')));
}

function renderField(f, fi) {
    const t = TYPES[f.type], probs = fieldProblems(f);
    const isSel = sel.kind === 'field' && sel.id === f.id;
    const select = () => { sel = { kind: 'field', id: f.id }; render(); };
    const el = h('div', { class: 'cfb-field' + (isSel ? ' cfb-sel' : ''), 'data-id': f.id, tabindex: 0, draggable: true,
        onclick: select,
        onkeydown: e => {
            if (e.target !== el) return;
            if (e.key === 'Enter') select();
            if (e.altKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) { e.preventDefault(); moveField(f.id, e.key === 'ArrowUp' ? -1 : 1); }
        },
        ondragstart: e => { e.dataTransfer.setData('text/x-cfb-field', f.id); e.dataTransfer.effectAllowed = 'move'; requestAnimationFrame(() => el.classList.add('cfb-dragging')); },
        ondragend: () => el.classList.remove('cfb-dragging') },
        h('span', { class: 'cfb-grip', icon: 'grip' }));
    const top = h('div', { class: 'cfb-field-top' });
    if (t.layout) top.append(h('span', { class: 'cfb-pill', text: 'Instructions' }));
    else {
        top.append(h('span', { class: 'cfb-qlabel' + (f.label.trim() ? '' : ' cfb-missing'), text: f.label.trim() || 'Untitled question' }));
        if (f.required) top.append(h('span', { class: 'cfb-req', 'aria-label': 'required', text: '*' }));
        top.append(h('span', { class: 'cfb-pill' + (t.linked ? ' cfb-accent' : ''), text: t.linked ? 'Profile: ' + t.label.toLowerCase() : t.label }));
    }
    if (hasCorrect(f)) top.append(h('span', { class: 'cfb-pill cfb-accent', text: 'Has a correct answer' }));
    else if (isQuiz() && t.correct) top.append(h('span', { class: 'cfb-pill cfb-warn', text: 'No correct answer' }));
    el.append(top);
    if (f.help && !t.layout) el.append(h('p', { class: 'cfb-qhelp', text: f.help }));
    el.append(h('div', { class: 'cfb-ctl', 'aria-hidden': 'true' }, controlPreview(f)));
    probs.forEach(p => el.append(h('p', { class: 'cfb-problem', text: p })));
    el.append(h('div', { class: 'cfb-field-tools' },
        iconBtn('up', 'Move up', e => { e.stopPropagation(); moveField(f.id, -1); }),
        iconBtn('down', 'Move down', e => { e.stopPropagation(); moveField(f.id, 1); }),
        iconBtn('copy', 'Duplicate', e => { e.stopPropagation(); duplicateField(f.id); }),
        iconBtn('trash', 'Delete', e => { e.stopPropagation(); deleteField(f.id); }, 'cfb-del')));
    return el;
}

function choicesFor(f) {
    if (TYPES[f.type].options) return f.options;
    return { boolean: ['Yes'], null_boolean: ['Unknown', 'Yes', 'No'], radio_yesno: ['Yes', 'No'], gender: ['Male', 'Female', 'Other'] }[f.type] || null;
}
function controlPreview(f) {
    const t = TYPES[f.type];
    if (t.layout) return h('div', { class: 'cfb-instructions-block' }, f.label ? h('strong', { text: f.label }) : null, f.help || (f.label ? '' : 'Write the instructions in the panel on the right.'));
    if (t.unknown) return h('p', { class: 'cfb-hint', text: 'This question type (' + f.type + ') can’t be edited here. It is kept as it is when you save.' });
    if (t.linked) return h('input', { type: 'text', placeholder: 'Pre-filled from their profile', tabindex: -1 });
    const correct = (f.type === 'radio_yesno' ? { T: 0, F: 1 }[f.correct] : null);
    if (['radio', 'checkboxes', 'radio_yesno', 'boolean', 'gender'].includes(f.type)) {
        return h('div', { class: 'cfb-opts' }, choicesFor(f).map((o, i) => h('label', { class: 'cfb-opt' },
            h('input', { type: f.type === 'checkboxes' || f.type === 'boolean' ? 'checkbox' : 'radio', tabindex: -1 }), o || '(empty choice)',
            isCorrect(f, i) || correct === i ? h('span', { class: 'cfb-ok', text: 'Correct' }) : null)));
    }
    if (t.options || f.type === 'null_boolean' || f.type === 'state') {
        const first = f.type === 'state' ? 'Choose a state' : choicesFor(f).length ? 'Choose…' : 'No choices yet';
        return h('select', { tabindex: -1, multiple: f.type === 'multiselect', size: f.type === 'multiselect' ? 3 : null },
            f.type === 'multiselect' ? choicesFor(f).slice(0, 3).map(o => h('option', { text: o })) : h('option', { text: first }));
    }
    if (f.type === 'longAns' || f.type === 'reallyLongAns') return h('textarea', { rows: f.type === 'longAns' ? 2 : 3, tabindex: -1 });
    if (f.type === 'file') return h('div', { class: 'cfb-empty-drop', text: 'Choose a file' });
    const placeholder = { numeric: 'A whole number' + rangeText(f), date: 'mm/dd/yyyy', time: 'hh:mm', email: 'name@example.org', phone: '(555) 555-0123', pronoun: 'e.g. she/her' }[f.type] || '';
    return h('input', { type: 'text', placeholder, tabindex: -1 });
}
function rangeText(f) {
    if (blank(f.min) && blank(f.max)) return '';
    return ' (' + (blank(f.min) ? '…' : f.min) + ' to ' + (blank(f.max) ? '…' : f.max) + ')';
}

// ---------- Drag and drop, moving and deleting ----------
function wireDrop(list, si) {
    let line = null;
    const clear = () => { if (line) line.remove(); line = null; };
    const cards = () => [...list.querySelectorAll('.cfb-field:not(.cfb-dragging)')];
    const indexAt = y => cards().filter(c => { const r = c.getBoundingClientRect(); return y > r.top + r.height / 2; }).length;
    list.addEventListener('dragover', e => {
        const types = e.dataTransfer.types;
        if (!types.includes('text/x-cfb-type') && !types.includes('text/x-cfb-field')) return;
        e.preventDefault();
        const at = indexAt(e.clientY), cs = cards();
        if (!line) line = h('div', { class: 'cfb-drop-line' });
        if (at < cs.length) list.insertBefore(line, cs[at]); else list.append(line);
    });
    list.addEventListener('dragleave', e => { if (!list.contains(e.relatedTarget)) clear(); });
    list.addEventListener('drop', e => {
        e.preventDefault();
        const at = indexAt(e.clientY); clear();
        const type = e.dataTransfer.getData('text/x-cfb-type'), id = e.dataTransfer.getData('text/x-cfb-field');
        if (type) addField(type, { pi: pageIx, si, at });
        else if (id) moveFieldTo(id, pageIx, si, at);
    });
}
function moveFieldTo(id, pi, si, at) {
    const loc = find(id); if (!loc) return;
    //   indexAt() already leaves out the card being dragged
    if (loc.pi === pi && loc.si === si && loc.fi === at) return;
    commit(s => { const [f] = s.pages[loc.pi].sections[loc.si].fields.splice(loc.fi, 1); s.pages[pi].sections[si].fields.splice(at, 0, f); });
}
function moveFieldToPage(id, pi) {
    const p = state.pages[pi], si = p.sections.length - 1;
    moveFieldTo(id, pi, si, p.sections[si].fields.length);
    pageIx = pi; sel = { kind: 'field', id }; render(); toast('Moved to page ' + (pi + 1));
}
function moveField(id, dir) {
    const loc = find(id), sec = loc.section;
    if ((dir < 0 && loc.fi === 0) || (dir > 0 && loc.fi === sec.fields.length - 1)) {
        //   Move into the neighbouring section on the same page
        const nsi = loc.si + dir, secs = loc.page.sections;
        if (nsi < 0 || nsi >= secs.length) return;
        commit(s => { const [f] = s.pages[loc.pi].sections[loc.si].fields.splice(loc.fi, 1); const t = s.pages[loc.pi].sections[nsi].fields; if (dir < 0) t.push(f); else t.unshift(f); });
    } else commit(s => { const fs = s.pages[loc.pi].sections[loc.si].fields; const [f] = fs.splice(loc.fi, 1); fs.splice(loc.fi + dir, 0, f); });
    requestAnimationFrame(() => { const el = document.querySelector('[data-id="' + id + '"]'); if (el) el.focus(); });
}
function duplicateField(id) {
    const loc = find(id);
    const copy = JSON.parse(JSON.stringify(loc.field));
    Object.assign(copy, { id: uid(), serverId: null, savedType: null, label: copy.label ? (copy.label + ' (copy)').slice(0, LIMITS.label) : '' });
    commit(s => s.pages[loc.pi].sections[loc.si].fields.splice(loc.fi + 1, 0, copy));
    sel = { kind: 'field', id: copy.id }; render();
}
function deleteField(id) {
    const loc = find(id);
    commit(s => s.pages[loc.pi].sections[loc.si].fields.splice(loc.fi, 1));
    if (sel.id === id) sel = { kind: 'section', id: loc.section.id };
    render();
    toast('Question deleted.' + savedAnswersNote(savedCount([loc.field])), undo);
}
function deleteSection(id) {
    const loc = find(id), n = loc.section.fields.length, saved = savedCount(loc.section.fields);
    const lastOnPage = loc.page.sections.length === 1;
    if (lastOnPage && state.pages.length === 1) { toast('A form needs at least one section.'); return; }
    sel = { kind: 'form' };
    //   A page's last section takes the page with it, so no empty page is left behind
    commit(s => { if (lastOnPage) { s.pages.splice(loc.pi, 1); pageIx = Math.max(0, loc.pi - 1); } else s.pages[loc.pi].sections.splice(loc.si, 1); });
    toast((lastOnPage ? 'Section and page ' + (loc.pi + 1) + ' deleted' : 'Section deleted') + (n ? ' with ' + plural(n, 'question') : '') + '.' + savedAnswersNote(saved), undo);
}
function deletePage(pi) {
    const fields = state.pages[pi].sections.flatMap(s => s.fields);
    sel = { kind: 'form' };
    //   Show the page before the deleted one (or the new first page)
    commit(s => { s.pages.splice(pi, 1); pageIx = Math.max(0, pi - 1); });
    toast('Page deleted' + (fields.length ? ' with ' + plural(fields.length, 'question') : '') + '.' + savedAnswersNote(savedCount(fields)), undo);
}

// ---------- Inspector ----------
function renderInspector() {
    const root = document.getElementById('cfb-inspector'); root.replaceChildren();
    if (mode === 'preview') {
        root.append(h('h2', { text: 'Previewing' }),
            h('p', { class: 'cfb-sub', text: 'Roughly what respondents see. Profile questions are pre-filled for them, and nothing is submitted here.' }),
            h('button', { type: 'button', class: 'cfb-btn', style: 'justify-self:start', onclick: () => { resetPreview(); render(); } }, 'Start over'));
        return;
    }
    if (sel.kind === 'field') { const loc = find(sel.id); if (loc) return fieldInspector(root, loc); sel = { kind: 'form' }; }
    if (sel.kind === 'section') { const loc = find(sel.id); if (loc) return sectionInspector(root, loc); sel = { kind: 'form' }; }
    formInspector(root);
}
function row(label, control, help, id) {
    return h('div', { class: 'cfb-row' }, h('label', { for: id, text: label }), control, help ? h('div', { class: 'cfb-help', text: help }) : null);
}
function textInput(id, value, onInput, attrs) { return h('input', Object.assign({ id, type: 'text', value: value || '', oninput: e => onInput(e.target.value) }, attrs || {})); }
function textArea(id, value, onInput, rows, attrs) { return h('textarea', Object.assign({ id, rows: rows || 2, oninput: e => onInput(e.target.value) }, attrs || {}), value || ''); }
function selectBox(id, options, value, onChange, attrs) {
    return h('select', Object.assign({ id, onchange: e => onChange(e.target.value) }, attrs || {}),
        options.map(([v, label, disabled]) => h('option', { value: v, text: label, selected: String(v) === String(value), disabled: !!disabled })));
}
function toggle(id, label, checked, onChange, disabled, help) {
    return h('div', { class: 'cfb-row' }, h('div', { class: 'cfb-switch' }, h('label', { for: id, text: label }),
        h('input', { id, type: 'checkbox', role: 'switch', checked, disabled, onchange: e => onChange(e.target.checked) })), help ? h('div', { class: 'cfb-help', text: help }) : null);
}
const live = (mutate, key) => commit(mutate, { key, keepInspector: true });
const change = mutate => commit(mutate, { keepInspector: false });

function allowedTypes(f) {
    const saved = f.savedType && TYPES[f.savedType];
    if (saved && (saved.linked || saved.unknown)) return [f.savedType];
    if (saved) return [f.savedType, ...(SAFE_CHANGES[f.savedType] || [])];
    return Object.keys(TYPES).filter(k => k === f.type || (!TYPES[k].unknown && !(TYPES[k].linked && state.settings.anonymous)));
}
function changeType(id, nt) {
    change(s => {
        const f = find(id).field, old = TYPES[f.type], t = TYPES[nt];
        f.type = nt; f.extra = {};
        if (t.options && !f.options) f.options = ['Option 1', 'Option 2'];
        if (!t.options) delete f.options;
        if (t.text) { f.charMin = f.charMin || ''; f.charMax = f.charMax || ''; } else { delete f.charMin; delete f.charMax; }
        if (nt === 'numeric') { f.min = f.min || ''; f.max = f.max || ''; } else { delete f.min; delete f.max; }
        //   Text answers carry over between the one-line and paragraph types
        const family = c => c === 'textarea' ? 'text' : c;
        if (family(old.correct) !== family(t.correct)) delete f.correct;
        if (t.linked) { f.linkId = '-1'; f.required = f.required || t.modelRequired; if (!f.label.trim()) f.label = t.ques; } else delete f.linkId;
        if (t.layout) f.required = false;
    });
}

function fieldInspector(root, loc) {
    const f = loc.field, t = TYPES[f.type], id = f.id;
    const upd = (k, key) => v => live(() => { find(id).field[k] = v; }, key || id + k);
    root.append(h('h2', { text: t.layout ? 'Instructions' : 'Question' }),
        h('p', { class: 'cfb-sub', text: 'Page ' + (loc.pi + 1) + ' · ' + (loc.section.title.trim() || 'Untitled section') + (f.serverId ? ' · saved' : ' · new') }));
    if (t.layout) {
        root.append(row('Heading', textInput('cfb-i-label', f.label, upd('label'), { maxlength: LIMITS.label }), 'Optional. Shown in bold above the text.', 'cfb-i-label'),
            row('Text', textArea('cfb-i-help', f.help, upd('help'), 5), null, 'cfb-i-help'));
    } else {
        root.append(row('Question', textInput('cfb-i-label', f.label, upd('label'), { maxlength: LIMITS.label }), null, 'cfb-i-label'),
            row('Help text', textArea('cfb-i-help', f.help, upd('help')), 'Shown under the question.', 'cfb-i-help'));
    }

    const types = allowedTypes(f);
    if (types.length > 1) {
        root.append(row('Type', selectBox('cfb-i-type', types.map(k => [k, (TYPES[k].linked ? 'Profile: ' : '') + TYPES[k].label]), f.type, v => changeType(id, v)),
            f.savedType ? 'This question is saved, so it can only change to types that keep its existing answers.' : null, 'cfb-i-type'));
    } else if (f.savedType && !t.layout) {
        root.append(h('div', { class: 'cfb-callout cfb-info', text: 'Type: ' + t.label + '. A saved question of this type can’t change type without losing its answers. To ask it differently, add a new question and delete this one.' }));
    }
    if (t.linked) root.append(h('div', { class: 'cfb-callout cfb-info', text: 'Pre-filled from the respondent’s ' + categoryName(t.category) + '. Their answer is saved with the response and also updates their profile.' }));

    if (!t.layout && !t.unknown) {
        const locked = t.linked && t.modelRequired;
        root.append(toggle('cfb-i-req', 'Required', f.required, v => change(() => { find(id).field.required = v; }), locked,
            locked ? 'This profile field is always required.' : null));
    }
    if (t.options) root.append(optionsEditor(f));
    if (f.type === 'numeric') root.append(h('div', { class: 'cfb-row' }, h('span', { class: 'cfb-lab', text: 'Allowed range' }),
        h('div', { class: 'cfb-two' },
            h('input', { type: 'number', step: 1, id: 'cfb-i-min', 'aria-label': 'Smallest', placeholder: 'Smallest', value: f.min, oninput: e => { upd('min')(e.target.value); refreshProblems(); } }),
            h('input', { type: 'number', step: 1, id: 'cfb-i-max', 'aria-label': 'Largest', placeholder: 'Largest', value: f.max, oninput: e => { upd('max')(e.target.value); refreshProblems(); } })),
        h('div', { class: 'cfb-help', text: 'Whole numbers. Leave either blank for no limit.' }), h('div', { class: 'cfb-err', id: 'cfb-i-err' })));
    if (t.text) root.append(h('div', { class: 'cfb-row' }, h('span', { class: 'cfb-lab', text: 'Answer length (characters)' }),
        h('div', { class: 'cfb-two' },
            h('input', { type: 'number', min: 0, step: 1, id: 'cfb-i-cmin', 'aria-label': 'Minimum length', placeholder: 'Minimum', value: f.charMin, oninput: e => { upd('charMin')(e.target.value); refreshProblems(); } }),
            h('input', { type: 'number', min: 1, max: t.cap || null, step: 1, id: 'cfb-i-cmax', 'aria-label': 'Maximum length', placeholder: t.cap ? 'Maximum (' + t.cap + ')' : 'Maximum', value: f.charMax, oninput: e => { upd('charMax')(e.target.value); refreshProblems(); } })),
        h('div', { class: 'cfb-help', text: t.cap ? 'Answers to this type are stored in at most ' + t.cap + ' characters. Use Paragraph for longer answers.' : 'Leave either blank for no limit.' }),
        h('div', { class: 'cfb-err', id: 'cfb-i-err' })));
    if (t.correct && !t.options) root.append(correctEditor(f));
    if (t.linked) root.append(linkedRecordEditor(f));
    if (state.pages.length > 1) {
        root.append(row('Page', selectBox('cfb-i-page', state.pages.map((p, i) => [i, 'Page ' + (i + 1)]), loc.pi, v => moveFieldToPage(id, Number(v))), null, 'cfb-i-page'));
    }
    root.append(h('hr', { class: 'cfb-sep' }), h('div', { class: 'cfb-tools' },
        h('button', { type: 'button', class: 'cfb-btn', onclick: () => duplicateField(id) }, 'Duplicate'),
        h('button', { type: 'button', class: 'cfb-btn cfb-danger-text', onclick: () => deleteField(id) }, 'Delete')));
    if (f.serverId && meta.formId) root.append(h('p', { class: 'cfb-help', style: 'font-size:.8rem;color:var(--cfb-muted)', text: 'Deleting a saved question also deletes its answers when you save.' }));
    refreshProblems();
}
function refreshProblems() {
    const err = document.getElementById('cfb-i-err');
    if (err && sel.kind === 'field') {
        const loc = find(sel.id);
        if (loc) err.textContent = fieldProblems(loc.field).filter(p => /length|value|number|characters/.test(p)).join(' ');
    }
}

function correctEditor(f) {
    const t = TYPES[f.type], id = f.id;
    const set = v => change(() => { find(id).field.correct = blank(v) ? null : v; });
    let control;
    if (t.correct === 'yesno') control = selectBox('cfb-i-correct', [['', 'Any answer'], ['T', 'Yes'], ['F', 'No']], f.correct || '', set);
    else if (t.correct === 'nullbool') control = selectBox('cfb-i-correct', [['', 'Any answer'], ['Unknown', 'Unknown'], ['Yes', 'Yes'], ['No', 'No']], f.correct || '', set);
    else if (t.correct === 'textarea') control = textArea('cfb-i-correct', f.correct || '', v => live(() => { find(id).field.correct = v; }, id + 'correct'), 2);
    else {
        const type = { number: 'number', date: 'date', time: 'time' }[t.correct] || 'text';
        control = h('input', { id: 'cfb-i-correct', type, value: f.correct || '', step: t.correct === 'number' ? 'any' : null,
            oninput: e => live(() => { find(id).field.correct = e.target.value; }, id + 'correct') });
    }
    return answerCheck(f, row('Correct answer', control, 'Respondents must give exactly this answer to continue. Leave blank to accept any answer.', 'cfb-i-correct'));
}
function answerCheck(f, content) {
    return h('details', { open: isQuiz() || hasCorrect(f) || null }, h('summary', { text: 'Answer checking' + (isQuiz() ? ' (quiz)' : '') }), content);
}

function optionsEditor(f) {
    const id = f.id, multi = TYPES[f.type].multi;
    const wrap = h('div', { class: 'cfb-row' }, h('span', { class: 'cfb-lab', text: 'Choices' }));
    const list = h('div', { class: 'cfb-optedit' });
    const checking = isQuiz() || hasCorrect(f) || !!f.checking;
    f.options.forEach((o, i) => {
        const inp = h('input', { type: 'text', id: 'cfb-opt-' + i, value: o, 'aria-label': 'Choice ' + (i + 1),
            oninput: e => live(() => { find(id).field.options[i] = e.target.value; }, id + 'opt' + i),
            onkeydown: e => { if (e.key === 'Enter') { e.preventDefault(); addOpt(i + 1); } } });
        const correct = checking ? h('input', { class: 'cfb-correct', type: multi ? 'checkbox' : 'radio', name: 'cfb-correct-' + id, title: 'Correct answer',
            'aria-label': 'Mark choice ' + (i + 1) + ' correct', checked: isCorrect(f, i),
            onchange: e => change(() => {
                const fld = find(id).field;
                if (multi) { const c = new Set(Array.isArray(fld.correct) ? fld.correct : []); if (e.target.checked) c.add(i); else c.delete(i); fld.correct = [...c].sort((a, b) => a - b); } else fld.correct = i;
            }) }) : h('span');
        list.append(h('div', { class: 'cfb-optrow' }, correct, inp,
            h('button', { type: 'button', class: 'cfb-mini', 'aria-label': 'Move choice up', disabled: i === 0, icon: 'up', onclick: () => moveOpt(i, -1) }),
            h('button', { type: 'button', class: 'cfb-mini', 'aria-label': 'Move choice down', disabled: i === f.options.length - 1, icon: 'down', onclick: () => moveOpt(i, 1) }),
            h('button', { type: 'button', class: 'cfb-mini', 'aria-label': 'Remove choice', icon: 'x', onclick: () => removeOpt(i) })));
    });
    function remapCorrect(fld, map) {
        if (fld.correct === undefined || fld.correct === null) return;
        if (Array.isArray(fld.correct)) fld.correct = fld.correct.map(map).filter(x => x !== null);
        else { const n = map(fld.correct); fld.correct = n === null ? null : n; }
    }
    function addOpt(at) {
        change(() => { const fld = find(id).field; fld.options.splice(at, 0, ''); remapCorrect(fld, c => c >= at ? c + 1 : c); });
        requestAnimationFrame(() => { const el = document.getElementById('cfb-opt-' + at); if (el) el.focus(); });
    }
    function removeOpt(i) { change(() => { const fld = find(id).field; fld.options.splice(i, 1); remapCorrect(fld, c => c === i ? null : c > i ? c - 1 : c); }); }
    function moveOpt(i, d) {
        change(() => { const fld = find(id).field; const [o] = fld.options.splice(i, 1); fld.options.splice(i + d, 0, o); remapCorrect(fld, c => c === i ? i + d : c === i + d ? i : c); });
    }
    function pasteOpts() {
        const box = h('textarea', { rows: 4, placeholder: 'One choice per line', 'aria-label': 'Choices, one per line' });
        const done = h('button', { type: 'button', class: 'cfb-btn', onclick: () => {
            const lines = box.value.split('\n').map(x => x.trim()).filter(Boolean);
            if (lines.length) change(() => { const fld = find(id).field; fld.options = lines; fld.correct = null; });
        } }, 'Replace choices');
        wrap.append(box, done); box.focus();
    }
    wrap.append(list, h('div', { class: 'cfb-tools' },
        h('button', { type: 'button', class: 'cfb-btn', onclick: () => addOpt(f.options.length) }, '+ Add choice'),
        h('button', { type: 'button', class: 'cfb-linkbtn', onclick: pasteOpts }, 'Paste a list'),
        !checking ? h('button', { type: 'button', class: 'cfb-linkbtn', onclick: () => change(() => { find(id).field.checking = true; }) }, 'Set a correct answer') : null),
        h('div', { class: 'cfb-help', text: (checking ? 'Tick the correct ' + (multi ? 'choices' : 'choice') + '; respondents must pick ' + (multi ? 'exactly those' : 'it') + ' to continue. ' : '') + 'Press Enter in a choice to add another.' }));
    if (checking && !isQuiz()) wrap.append(h('button', { type: 'button', class: 'cfb-linkbtn', style: 'justify-self:start', onclick: () => change(() => { const fld = find(id).field; fld.correct = null; fld.checking = false; }) }, 'Accept any answer'));
    return wrap;
}

function linkedRecordEditor(f) {
    const t = TYPES[f.type], id = f.id, particular = f.linkId !== '-1';
    const content = h('div', { class: 'cfb-row' });
    content.append(selectBox('cfb-i-linkmode', [['own', 'The respondent’s own record'], ['particular', 'One particular record']], particular ? 'particular' : 'own',
        v => change(() => { find(id).field.linkId = v === 'own' ? '-1' : ''; })));
    if (particular) {
        const list = linkTargets(t.category);
        if (list.status === 'loading') content.append(h('div', { class: 'cfb-help', text: 'Loading records…' }));
        else if (list.status === 'error') content.append(h('div', { class: 'cfb-err', text: list.error }));
        else content.append(selectBox('cfb-i-linkid', [['', 'Choose a record…', true], ...list.data.map(o => [String(o.id), o.name])], f.linkId,
            v => change(() => { find(id).field.linkId = v; })));
        if (f.linkId === '') content.append(h('div', { class: 'cfb-err', text: 'Choose a record, or switch back to the respondent’s own.' }));
    }
    return h('details', { open: particular || null }, h('summary', { text: 'Which record it updates' }), content);
}

function sectionInspector(root, loc) {
    const sec = loc.section, id = sec.id;
    root.append(h('h2', { text: 'Section' }), h('p', { class: 'cfb-sub', text: 'Page ' + (loc.pi + 1) + ' · ' + plural(sec.fields.length, 'question') }),
        row('Heading', textInput('cfb-s-title', sec.title, v => live(() => { find(id).section.title = v; }, id + 't'), { maxlength: LIMITS.sectionTitle }), 'Optional. Up to ' + LIMITS.sectionTitle + ' characters.', 'cfb-s-title'),
        row('Description', textArea('cfb-s-desc', sec.description, v => live(() => { find(id).section.description = v; }, id + 'd'), 3, { maxlength: LIMITS.sectionDesc }), 'Optional. Up to ' + LIMITS.sectionDesc + ' characters.', 'cfb-s-desc'));
    if (!sec.fields.length) root.append(h('div', { class: 'cfb-callout cfb-danger', text: canDeleteSection() ? 'This section has no questions. Add one, or delete the section, before saving.' : 'This section has no questions. Add one before saving.' }));
    if (loc.page.sections.length === 1 && state.pages.length > 1) root.append(h('div', { class: 'cfb-help', text: 'This is the only section on page ' + (loc.pi + 1) + ', so deleting it also deletes the page.' }));
    root.append(h('hr', { class: 'cfb-sep' }), h('button', { type: 'button', class: 'cfb-btn cfb-danger-text', style: 'justify-self:start', disabled: !canDeleteSection(), onclick: () => deleteSection(id) }, 'Delete section'));
}

function linkSentence(short) {
    const s = state.settings;
    if (isNone(s.linkType)) return short ? 'Standalone form' : 'This form isn’t linked to a program or class.';
    const kind = s.linkType.toLowerCase();
    if (s.linkId === -1) return short ? 'Respondents pick a ' + kind : 'Respondents choose which ' + kind + ' their answers are about.';
    const list = remote.links[s.linkType];
    const target = list && list.status === 'ok' ? (list.data.find(o => o.id === s.linkId) || {}).name : null;
    const name = target || s.linkType + ' #' + s.linkId;
    if (linkModuleApplies() && s.linkModule) return (MODULE_NAMES[s.linkModule] || s.linkModule) + (short ? ', ' : ' in ') + name;
    return (short ? 'Linked to ' : 'Answers are linked to ') + name;
}
function audienceSentence(short) {
    const s = state.settings;
    if (!s.role) {
        if (s.anonymous) return short ? 'Open to anyone' : 'Anyone with the link can fill this in, even without an account.';
        return short ? 'Anyone logged in' : 'Anyone who is logged in can fill this in.';
    }
    const who = ROLE_NAMES[s.role] || s.role;
    if (!s.permProgram || !s.permList) return short ? who + ' only' : 'Only ' + who.toLowerCase() + ' can fill this in.';
    const groups = remote.perms[s.permProgram];
    const g = groups && groups.status === 'ok' ? (groupsFor(groups.data, s.role) || []).find(([k]) => k === s.permList) : null;
    const prog = (CONFIG.programs.find(p => String(p.id) === s.permProgram) || {}).name || 'program #' + s.permProgram;
    const groupName = g ? g[1] : s.permList;
    return short ? who + ': ' + groupName : 'Only ' + who.toLowerCase() + ' in ' + prog + ' who are in “' + groupName + '” can fill this in.';
}

function formInspector(root) {
    const s = state.settings;
    const set = k => v => live(st => { st.settings[k] = v; }, 'set' + k);
    root.append(h('h2', { text: 'Form settings' }));
    if (meta.formId) root.append(h('p', { class: 'cfb-sub' }, h('a', { href: '/customforms/view/' + meta.formId + '/', target: '_blank', rel: 'noopener' }, 'Open the form'), ' · ',
        h('a', { href: '/customforms/responses/' + meta.formId + '/', target: '_blank', rel: 'noopener' }, 'View responses')));
    root.append(row('Description', textArea('cfb-f-desc', state.description, v => live(st => { st.description = v; }, 'desc'), 3), 'Shown at the top of the first page.', 'cfb-f-desc'));
    if (!meta.formId && CONFIG.forms.length) root.append(templatePicker());

    // Who can fill it in
    root.append(h('hr', { class: 'cfb-sep' }));
    const roles = [['', 'Anyone ' + (s.anonymous ? 'with the link' : 'logged in')], ['Teacher', 'Teachers'], ['Student', 'Students']];
    if (s.role && !ROLE_NAMES[s.role]) roles.push([s.role, s.role]);
    root.append(row('Who can fill it in', selectBox('cfb-f-role', roles, s.role, v => change(st => { Object.assign(st.settings, { role: v, permProgram: '', permList: '', permExtra: [] }); })), null, 'cfb-f-role'));
    if (s.role) {
        root.append(row('Limit to a group in a program', selectBox('cfb-f-prog', [['', 'Any (no program limit)'], ...CONFIG.programs.map(p => [String(p.id), p.name])], s.permProgram,
            v => change(st => { Object.assign(st.settings, { permProgram: v, permList: '', permExtra: [] }); })), null, 'cfb-f-prog'));
        if (s.permProgram) {
            const groups = permGroups(s.permProgram);
            if (groups.status === 'loading') root.append(h('p', { class: 'cfb-help', text: 'Loading groups…' }));
            else if (groups.status === 'error') root.append(h('div', { class: 'cfb-err', text: groups.error }));
            else {
                const list = groupsFor(groups.data, s.role) || [];
                if (!list.length) root.append(h('div', { class: 'cfb-callout cfb-warn', text: 'This program has no groups of ' + (ROLE_NAMES[s.role] || s.role).toLowerCase() + ' to choose from. Set the program to “Any”.' }));
                else {
                    const opts = [['', 'Choose a group…', true], ...list.map(([k, d]) => [k, d])];
                    if (s.permList && !list.some(([k]) => k === s.permList)) opts.push([s.permList, s.permList + ' (no longer available)']);
                    root.append(row('Group', selectBox('cfb-f-group', opts, s.permList, v => change(st => { st.settings.permList = v; st.settings.permExtra = []; })), null, 'cfb-f-group'));
                }
            }
        }
    }
    const linked = hasLinked();
    let anonHelp = 'Responses aren’t tied to an account, and people can respond more than once.';
    if (meta.formId) anonHelp = 'This can’t be changed after the form is created.';
    else if (linked && !s.anonymous) anonHelp = 'Remove the profile questions first: they save answers to the respondent’s own profile.';
    root.append(toggle('cfb-f-anon', 'Anonymous', s.anonymous, v => change(st => { st.settings.anonymous = v; }), !!meta.formId || (linked && !s.anonymous), anonHelp));
    root.append(h('div', { class: 'cfb-summary', text: audienceSentence(false) }));
    if (s.anonymous && linked) root.append(h('div', { class: 'cfb-callout cfb-danger', text: 'This form is anonymous but has profile questions. Remove them before saving.' }));

    // What it's linked to
    root.append(h('hr', { class: 'cfb-sep' }));
    if (LINK_MODELS.length) {
        root.append(row('Link answers to', selectBox('cfb-f-link', [['-1', 'Nothing'], ...LINK_MODELS.map(m => [m, 'A ' + m.toLowerCase()])], isNone(s.linkType) ? '-1' : s.linkType,
            v => change(st => { Object.assign(st.settings, { linkType: v, linkId: -1, linkModule: '' }); })), null, 'cfb-f-link'));
        if (!isNone(s.linkType)) {
            const list = linkTargets(s.linkType);
            let opts = [['-1', 'The respondent picks one']];
            if (list.status === 'ok') opts = opts.concat(list.data.map(o => [String(o.id), o.name]));
            else if (s.linkId !== -1) opts.push([String(s.linkId), s.linkType + ' #' + s.linkId]);
            root.append(row('Which ' + s.linkType.toLowerCase(), selectBox('cfb-f-linkid', opts, String(s.linkId),
                v => change(st => { Object.assign(st.settings, { linkId: Number(v), linkModule: '' }); })), list.status === 'loading' ? 'Loading…' : list.status === 'error' ? list.error : null, 'cfb-f-linkid'));
            if (linkModuleApplies()) root.append(moduleRow());
        }
        if (meta.formId && !isNone(meta.savedLinkType) && s.linkType !== meta.savedLinkType) {
            root.append(h('div', { class: 'cfb-callout cfb-danger', text: 'Changing what this form is linked to deletes the ' + meta.savedLinkType.toLowerCase() + ' saved with each existing response.' }));
        }
        root.append(h('div', { class: 'cfb-summary', text: linkSentence(false) }));
    }

    // After submitting
    root.append(h('hr', { class: 'cfb-sep' }));
    root.append(row('After submitting, show', textArea('cfb-f-msg', s.successMessage, set('successMessage'), 2, { maxlength: LIMITS.successMessage }), null, 'cfb-f-msg'));
    const urlErr = h('div', { class: 'cfb-err' });
    const checkUrl = v => { urlErr.textContent = v.trim() && !/^(https?:\/\/|\/)/i.test(v.trim()) ? 'Use a link starting with /, http:// or https://.' : ''; };
    root.append(row('Then send them to', textInput('cfb-f-url', s.successUrl, v => { set('successUrl')(v); checkUrl(v); }, { inputmode: 'url', placeholder: '/learn/…/studentreg', maxlength: LIMITS.successUrl }),
        'Optional. Leave blank to stay on the thank-you page.', 'cfb-f-url'), urlErr);
    checkUrl(s.successUrl);
}
function moduleRow() {
    const s = state.settings, mods = programModules(String(s.linkId));
    const opts = [['', 'Not a registration step']];
    if (mods.status === 'ok') {
        mods.data.learn.concat(mods.data.teach).forEach(([handler]) => { if (!opts.some(([v]) => v === handler)) opts.push([handler, MODULE_NAMES[handler] || handler]); });
    }
    if (s.linkModule && !opts.some(([v]) => v === s.linkModule)) opts.push([s.linkModule, (MODULE_NAMES[s.linkModule] || s.linkModule) + (mods.status === 'ok' ? ' (not enabled)' : '')]);
    let help = 'Adds this form as a step in that program’s registration.';
    if (mods.status === 'loading') help = 'Loading registration modules…';
    else if (mods.status === 'error') help = mods.error;
    else if (opts.length === 1) help = 'To add this form to registration, first enable the Student Custom Form, Teacher Custom Form or Teacher Logistics Quiz module for this program.';
    else if (s.linkModule === 'TeacherQuizModule') help = 'Quiz: teachers must give the correct answer to every question that has one. Set them under “Answer checking” on each question.';
    return row('Use in registration', selectBox('cfb-f-module', opts, s.linkModule, v => change(st => { st.settings.linkModule = v; })), help, 'cfb-f-module');
}
function templatePicker() {
    const pick = selectBox('cfb-f-template', [['', 'Choose a form…'], ...CONFIG.forms.map(f => [String(f.id), f.title + ' (#' + f.id + ')'])], '', () => null);
    const status = h('div', { class: 'cfb-help' });
    const load = h('button', { type: 'button', class: 'cfb-btn', onclick: async () => {
        if (!pick.value) return;
        if (dirty() && !window.confirm('Replace what you have so far with a copy of this form? You can undo this.')) return;
        load.disabled = true; status.textContent = 'Loading…';
        try {
            const md = await getJSON(URLS.metadata, { form_id: pick.value });
            const copy = fromMetadata(md, true);
            commit(() => { state = copy; });
            pageIx = 0; sel = { kind: 'form' }; render();
            toast('Copied “' + (md.title || 'form') + '”. Saving creates a new form.', undo);
        } catch (e) { status.textContent = e.message; load.disabled = false; }
    } }, 'Copy');
    return h('div', { class: 'cfb-row' }, h('label', { for: 'cfb-f-template', text: 'Start from a copy of' }),
        h('div', { style: 'display:flex;gap:6px' }, pick, load), status);
}

// ---------- Preview (respondent view) ----------
function resetPreview() { pv = { step: 0, answers: {}, errors: {}, done: false }; }
function renderPreview() {
    const root = document.getElementById('cfb-canvas'); root.replaceChildren();
    const wrap = h('div', { class: 'cfb-pv-wrap' }), s = state.settings;
    if (pv.done) {
        wrap.append(h('div', { class: 'cfb-pv cfb-done' }, h('h2', { text: 'Thank you' }), h('p', { text: s.successMessage || 'Your response has been recorded.' }),
            s.successUrl ? h('p', { class: 'cfb-hint', text: 'Next, they’re sent to ' + s.successUrl }) : null,
            h('button', { type: 'button', class: 'cfb-btn', style: 'justify-self:center', onclick: () => { resetPreview(); render({ inspector: false }); } }, 'Fill it in again')));
        root.append(wrap); return;
    }
    const n = state.pages.length;
    //   Undo can remove pages while previewing
    pv.step = Math.min(pv.step, n - 1);
    wrap.append(h('div', { class: 'cfb-pv-progress', 'aria-label': 'Page ' + (pv.step + 1) + ' of ' + n }, state.pages.map((p, i) => h('span', { class: i <= pv.step ? 'cfb-on' : '' }))));
    if (pv.step === 0) wrap.append(h('div', { class: 'cfb-formhead', style: 'cursor:default' }, h('h1', { text: state.title || 'Untitled form' }), state.description ? h('p', { text: state.description }) : null));
    const form = h('form', { class: 'cfb-pv-form', novalidate: true, onsubmit: e => { e.preventDefault(); next(); } });
    state.pages[pv.step].sections.forEach((sec, si) => {
        const box = h('div', { class: 'cfb-pv' }, sec.title ? h('h2', { text: sec.title }) : null, sec.description ? h('p', { class: 'cfb-hint', style: 'margin-top:-12px', text: sec.description }) : null);
        //   The server adds the program/class question to the first section of the first page
        if (pv.step === 0 && si === 0 && !isNone(s.linkType) && s.linkId === -1) {
            box.append(h('div', { class: 'cfb-row' }, h('label', { class: 'cfb-plabel', for: 'cfb-pv-link', text: s.linkType }),
                h('select', { id: 'cfb-pv-link' }, h('option', { text: 'Choose a ' + s.linkType.toLowerCase() + '…' }))));
        }
        sec.fields.forEach(f => box.append(pvField(f)));
        if (sec.fields.length) form.append(box);
    });
    form.append(h('div', { class: 'cfb-pv-nav' },
        pv.step > 0 ? h('button', { type: 'button', class: 'cfb-btn', onclick: () => { pv.step--; pv.errors = {}; render({ inspector: false }); } }, 'Back') : h('span'),
        h('button', { type: 'submit', class: 'cfb-btn cfb-primary' }, pv.step < n - 1 ? 'Next' : 'Submit')));
    wrap.append(form);
    root.append(wrap);
}
function pvField(f) {
    const t = TYPES[f.type], a = pv.answers, id = 'cfb-pv-' + f.id, err = pv.errors[f.id];
    if (t.layout) return h('div', { class: 'cfb-instructions-block' }, f.label ? h('strong', { text: f.label }) : null, f.help);
    if (t.unknown) return h('p', { class: 'cfb-hint', text: f.label + ' (' + f.type + ')' });
    const set = v => { a[f.id] = v; };
    const desc = [f.help ? id + '-h' : null, err ? id + '-e' : null].filter(Boolean).join(' ') || null;
    const common = { id, 'aria-describedby': desc, 'aria-invalid': err ? 'true' : null, 'aria-required': f.required ? 'true' : null };
    const label = h('label', { for: id, class: 'cfb-plabel' }, f.label, f.required ? h('span', { class: 'cfb-req', text: ' *' }) : null);
    const choices = choicesFor(f);
    if (choices && f.type !== 'boolean' && ['dropdown', 'multiselect', 'null_boolean'].includes(f.type)) {
        const ctl = h('select', Object.assign({ multiple: f.type === 'multiselect', onchange: e => set(f.type === 'multiselect' ? [...e.target.selectedOptions].map(o => o.value) : e.target.value) }, common),
            f.type === 'multiselect' ? null : h('option', { value: '', text: 'Choose…' }),
            choices.map(o => h('option', { value: o, text: o, selected: Array.isArray(a[f.id]) ? a[f.id].includes(o) : a[f.id] === o })));
        return h('div', { class: 'cfb-row' }, label, help(f, id), ctl, perr(err, id));
    }
    if (choices) {
        const multi = f.type === 'checkboxes' || f.type === 'boolean';
        return h('fieldset', { 'aria-describedby': desc }, h('legend', {}, f.label, f.required ? h('span', { class: 'cfb-req', text: ' *' }) : null), help(f, id),
            h('div', { class: 'cfb-opts' }, choices.map(o => h('label', { class: 'cfb-opt' }, h('input', { type: multi ? 'checkbox' : 'radio', name: id, value: o,
                checked: Array.isArray(a[f.id]) ? a[f.id].includes(o) : a[f.id] === o,
                onchange: e => { if (multi) { const c = new Set(a[f.id] || []); if (e.target.checked) c.add(o); else c.delete(o); set([...c]); } else set(o); } }), o))), perr(err, id));
    }
    let ctl;
    if (f.type === 'longAns' || f.type === 'reallyLongAns') ctl = h('textarea', Object.assign({ rows: f.type === 'longAns' ? 3 : 6, oninput: e => set(e.target.value) }, common), a[f.id] || '');
    else if (f.type === 'file') ctl = h('input', Object.assign({ type: 'file', onchange: e => set(e.target.files[0] ? e.target.files[0].name : '') }, common));
    else ctl = h('input', Object.assign({ type: { numeric: 'number', date: 'date', time: 'time', email: 'email', phone: 'tel' }[f.type] || 'text',
        value: a[f.id] || '', oninput: e => set(e.target.value) }, common));
    return h('div', { class: 'cfb-row' }, label, help(f, id),
        t.linked ? h('span', { class: 'cfb-prefilled', text: 'Pre-filled from their profile. Changing it updates their profile.' }) : null, ctl, perr(err, id));
}
const help = (f, id) => f.help ? h('span', { class: 'cfb-hint', id: id + '-h', style: 'margin:0', text: f.help }) : null;
const perr = (e, id) => e ? h('span', { class: 'cfb-perr', id: id + '-e', text: e }) : null;
function previewError(f, v) {
    const t = TYPES[f.type];
    const empty = v === undefined || v === '' || (Array.isArray(v) && !v.length);
    if (f.required && empty) return 'This field is required.';
    if (empty) return null;
    if (f.type === 'numeric') {
        const n = Number(v);
        if (!Number.isInteger(n)) return 'Enter a whole number.';
        if ((INT.test(f.min) && n < Number(f.min)) || (INT.test(f.max) && n > Number(f.max))) return 'Enter a number' + rangeText(f) + '.';
    }
    if (f.type === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) return 'Enter a valid email address.';
    if (t.text && typeof v === 'string') {
        const max = NONNEG_INT.test(f.charMax) ? Number(f.charMax) : t.cap;
        if (NONNEG_INT.test(f.charMin) && v.length < Number(f.charMin)) return 'Write at least ' + f.charMin + ' characters.';
        if (max && v.length > max) return 'Write at most ' + max + ' characters.';
    }
    if (hasCorrect(f)) {
        let want, got = Array.isArray(v) ? [...v].sort().join('|') : String(v);
        if (t.correct === 'one') want = f.options[f.correct];
        else if (t.correct === 'many') want = f.correct.map(i => f.options[i]).sort().join('|');
        else if (t.correct === 'yesno') want = { T: 'Yes', F: 'No' }[f.correct];
        else if (t.correct === 'number') { want = String(Number(f.correct)); got = String(Number(v)); }
        else want = String(f.correct);
        if (want !== got) return 'That’s not the right answer.';
    }
    return null;
}
function next() {
    const errs = {};
    state.pages[pv.step].sections.forEach(sec => sec.fields.forEach(f => {
        if (TYPES[f.type].layout || TYPES[f.type].unknown) return;
        const e = previewError(f, pv.answers[f.id]);
        if (e) errs[f.id] = e;
    }));
    pv.errors = errs;
    if (Object.keys(errs).length) {
        render({ inspector: false });
        requestAnimationFrame(() => { const el = document.querySelector('[aria-invalid="true"], fieldset .cfb-perr'); if (el && el.focus) el.focus(); });
        return;
    }
    if (pv.step < state.pages.length - 1) { pv.step++; render({ inspector: false }); window.scrollTo({ top: 0 }); } else { pv.done = true; render({ inspector: false }); }
}

// ---------- Saving and loading ----------
let toastTimer;
function toast(msg, action) {
    const t = document.getElementById('cfb-toast'); t.replaceChildren(h('span', { text: msg }));
    if (action) t.append(h('button', { type: 'button', text: 'Undo', onclick: () => { action(); t.hidden = true; } }));
    t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, action ? 7000 : 3000);
}
function showAlert(msg) { const a = document.getElementById('cfb-alert'); a.textContent = msg || ''; a.hidden = !msg; }

function loadSaved(md, formId) {
    meta.formId = formId; meta.savedLinkType = md.link_type || '-1';
    state = fromMetadata(md, false);
    hist = []; fut = []; lastKey = null;
    markSaved();
    sel = { kind: 'form' }; pageIx = Math.min(pageIx, state.pages.length - 1);
}
async function save() {
    const probs = formProblems();
    if (probs.length) { goToProblem(probs); return; }
    if (saving) return;
    saving = true; showAlert(''); renderTop();
    const editing = !!meta.formId;
    let message = null;
    try {
        const r = await request(editing ? URLS.modify : URLS.submit, { method: 'POST', body: JSON.stringify(toServer()),
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() } });
        if (!(r.res.ok && r.text === 'OK')) message = serverMessage(r.res, r.data);
    } catch (e) {
        message = 'Could not reach the server. Your changes are still here; check your connection and save again.';
    }
    if (message) {
        saving = false; showAlert('Not saved: ' + message); renderTop(); return;
    }
    if (!editing) {
        markSaved();
        window.location.href = URLS.landing;
        return;
    }
    //   Reload so new pages, sections and questions pick up their saved ids
    try {
        loadSaved(await getJSON(URLS.metadata, { form_id: meta.formId }), meta.formId);
        toast('Saved');
    } catch (e) {
        markSaved();
        showAlert('Saved, but the form couldn’t be reloaded: ' + e.message + '\nReload the page before making more changes.');
        meta.fatal = true;
    }
    saving = false; render();
}

async function init() {
    try {
        registerLinkTypes(await getJSON(URLS.buildData));
    } catch (e) {
        fatal('The form builder couldn’t load: ' + e.message); return;
    }
    state = blankState();
    markSaved();
    if (CONFIG.edit_error) showAlert(CONFIG.edit_error);
    if (CONFIG.edit) {
        try { loadSaved(await getJSON(URLS.metadata, { form_id: CONFIG.edit }), CONFIG.edit); }
        catch (e) { fatal('Form ' + CONFIG.edit + ' couldn’t be loaded: ' + e.message); return; }
    }
    meta.loaded = true;
    render();
}
function fatal(msg) {
    meta.fatal = true; showAlert(msg);
    document.getElementById('cfb-canvas').replaceChildren(h('p', { class: 'cfb-loading' }, 'Nothing to show. ', h('a', { href: URLS.landing, text: 'Back to custom forms' })));
    ['cfb-save', 'cfb-undo', 'cfb-redo', 'cfb-settings', 'cfb-m-edit', 'cfb-m-preview'].forEach(id => { document.getElementById(id).disabled = true; });
}

// ---------- Wiring ----------
document.getElementById('cfb-title').addEventListener('input', e => { if (state) live(s => { s.title = e.target.value; }, 'title'); });
document.getElementById('cfb-undo').onclick = undo;
document.getElementById('cfb-redo').onclick = redo;
document.getElementById('cfb-save').onclick = save;
document.getElementById('cfb-m-edit').onclick = () => { mode = 'edit'; render(); };
document.getElementById('cfb-m-preview').onclick = () => { mode = 'preview'; resetPreview(); render(); window.scrollTo({ top: 0 }); };
document.getElementById('cfb-settings').onclick = () => {
    mode = 'edit'; sel = { kind: 'form' }; render();
    //   On narrow screens the settings sit below the form, so bring them into view
    const insp = document.getElementById('cfb-inspector');
    if (window.matchMedia('(max-width: 760px)').matches) insp.scrollIntoView({ behavior: 'smooth', block: 'start' });
    const first = insp.querySelector('textarea, input, select'); if (first) first.focus({ preventScroll: true });
};
document.addEventListener('keydown', e => {
    if (!state) return;
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && !typing) { e.preventDefault(); if (e.shiftKey) redo(); else undo(); }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); if (!document.getElementById('cfb-save').disabled) save(); }
    if ((e.key === 'Delete' || e.key === 'Backspace') && !typing && sel.kind === 'field' && mode === 'edit' && document.activeElement.classList.contains('cfb-field')) { e.preventDefault(); deleteField(sel.id); }
});
const topbar = document.querySelector('.cfb-topbar');
new ResizeObserver(() => document.getElementById('cfb-app').style.setProperty('--cfb-top-h', topbar.offsetHeight + 'px')).observe(topbar);
if (window.matchMedia('(max-width: 1100px)').matches) document.getElementById('cfb-pal-details').open = false;
window.addEventListener('beforeunload', e => { if (dirty() && !saving) { e.preventDefault(); e.returnValue = ''; } });
init();
})();
