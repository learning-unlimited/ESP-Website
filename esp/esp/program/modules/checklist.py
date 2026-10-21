"""Context helpers for the registration checklist (checklist_sidebar.html and
checkboxes.html), shared by the registration main pages and module pages."""

from django.core.exceptions import ObjectDoesNotExist

MAINPAGE_VIEWS = {'learn': 'studentreg', 'teach': 'teacherreg'}


def get_checklist_context(user, prog, tl, modules=None):
    """Return the checklist context for ``user`` in the ``tl`` ('learn' or
    'teach') registration for ``prog``.

    Pass ``modules`` to reuse a list already fetched with prog.getModules().
    The modules are listed in the order users meet them: when registration
    forces required modules, those come first; otherwise by seq.  Modules
    outside their schedule window are listed too, with ``checklist_only``
    set so the main pages don't render them; each module gets a
    ``schedule_state`` of 'open', 'upcoming' or 'closed'.
    """
    # Imported here because studentregcore uses this module for its main page.
    from esp.program.modules.handlers.studentregcore import StudentRegCore

    if modules is None:
        modules = prog.getModules(user, tl)
    open_modules = list(modules)
    listed = {m.id for m in open_modules}
    others = [m for m in prog.getModules(tl=tl) if m.id not in listed]
    for m in open_modules:
        m.checklist_only = False
    for m in others:
        m.user = user
        m.checklist_only = True
    forced = forces_required_modules(prog)
    modules = sorted(open_modules + others, key=lambda m: (forced and not m.isRequired(), m.seq))
    for m in modules:
        m.schedule_state = 'closed' if m.has_ended() else ('upcoming' if not m.is_valid() else 'open')
        m.opens_on = m.start_date if m.schedule_state == 'upcoming' else None
        m.after_gate = None
        m.hide_in_checklist = False

    checklist = {
        'modules': modules,
        'completedAll': not any(
            not m.isCompleted(user) and m.isRequired()
            for m in open_modules
        ),
        'records': StudentRegCore.get_reg_records(user, prog, tl),
        'extra_steps': '%s:extra_steps' % tl,
        'program': prog,
        'gate': None,
        'gate_status': None,
    }
    if forced:
        _add_gates(checklist, user)
    return checklist


def _add_gates(checklist, user):
    """Describe the lotteries (gating modules) ahead of or holding the user.

    Sets ``gate`` and ``gate_status`` when the required-module flow is
    holding the user at a gating module, and marks each module with the last
    unpassed gate listed before it (``after_gate``), moving its ``opens_on``
    date to when that gate closes if that is later.  Once a gate refuses the
    user, the steps after it and the other requirements are hidden.
    """
    from esp.program.modules.base import CoreModule

    required = [m for m in checklist['modules']
                if m.isRequired() and m.main_view and not isinstance(m, CoreModule)]
    statuses = {m.id: m.gate_status(user) for m in required}
    stop = next((m for m in required if statuses[m.id] != 'passed'), None)
    if stop is not None and stop.gate_lifts:
        checklist['gate'] = stop
        checklist['gate_status'] = statuses[stop.id]

    gate = None
    for m in checklist['modules']:
        m.after_gate = gate
        if gate is not None and gate.gate_lifts == 'closed' and gate.end_date:
            m.opens_on = max(m.opens_on or gate.end_date, gate.end_date)
        if m.gate_lifts and statuses.get(m.id, 'passed') != 'passed':
            gate = m
    if checklist['gate_status'] == 'refused':
        for m in checklist['modules']:
            m.hide_in_checklist = m.after_gate is not None
        checklist['records'] = []


def forces_required_modules(prog):
    """True if registration makes users complete required modules in order."""
    try:
        return prog.studentclassregmoduleinfo.force_show_required_modules
    except (AttributeError, ObjectDoesNotExist):
        return False


def get_checklist_progress(checklist, include_steps=True):
    """Summarize a checklist context for its progress bar.

    Counts the required registration steps (when ``include_steps``) and the
    other registration requirements (records).  Returns ``done``, ``total``,
    ``percent``, and the first unfinished item as ``next_step`` (a module) or
    ``next_record`` (a record dict).
    """
    steps = []
    if include_steps:
        steps = [(m, m.isCompleted()) for m in checklist['modules']
                 if m.isStep() and m.isRequired() and _counts_toward_progress(m)]
    records = checklist.get('records') or []

    done = sum(1 for m, completed in steps if completed) + sum(1 for r in records if r['isCompleted'])
    total = len(steps) + len(records)
    next_step = next((m for m, completed in steps if not completed), None)
    next_record = None if next_step else next((r for r in records if not r['isCompleted']), None)
    return {
        'done': done,
        'total': total,
        'percent': round(100 * done / total) if total else 100,
        'next_step': next_step,
        'next_record': next_record,
    }


def _counts_toward_progress(module):
    """Closed steps no longer count unless they were done, or still hold the
    user (a 'completed' gate such as the student lottery)."""
    if module.hide_in_checklist:
        return False
    if module.schedule_state != 'closed':
        return True
    return module.gate_lifts == 'completed' or module.isCompleted()


def get_module_page_checklist_context(user, prog, tl):
    """Like get_checklist_context(), but for a module page other than the
    main page, so checklist links point back to the main page."""
    context = get_checklist_context(user, prog, tl)
    context['is_module_page'] = True
    context['mainpage_url'] = '/%s/%s/%s' % (tl, prog.url, MAINPAGE_VIEWS[tl])
    return context
