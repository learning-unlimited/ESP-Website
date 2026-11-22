"""Context helpers for the registration checklist (checkboxes.html and
progressbar.html), shared by the registration main pages and module pages."""

from django.core.exceptions import ObjectDoesNotExist

from esp.program.modules.handlers.studentregcore import StudentRegCore

MAINPAGE_VIEWS = {'learn': 'studentreg', 'teach': 'teacherreg'}


def get_checklist_context(user, prog, tl, modules=None):
    """Return the checklist context for ``user`` in the ``tl`` ('learn' or
    'teach') registration for ``prog``.

    Pass ``modules`` to reuse a list already fetched with prog.getModules().
    The modules are listed in the order users meet them: when registration
    forces required modules, those come first; otherwise by seq.
    """
    if modules is None:
        modules = prog.getModules(user, tl)
    forced = forces_required_modules(prog)
    modules = sorted(modules, key=lambda m: (forced and not m.isRequired(), m.seq))

    return {
        'modules': modules,
        'completedAll': not any(
            not m.isCompleted(user) and m.isRequired()
            for m in modules
        ),
        'records': StudentRegCore.get_reg_records(user, prog, tl),
        'extra_steps': '%s:extra_steps' % tl,
        'program': prog,
    }


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
        steps = [(m, m.isCompleted()) for m in checklist['modules'] if m.isStep() and m.isRequired()]
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


def get_module_page_checklist_context(user, prog, tl):
    """Like get_checklist_context(), but for a module page other than the
    main page, so checklist links point back to the main page."""
    context = get_checklist_context(user, prog, tl)
    context['is_module_page'] = True
    context['mainpage_url'] = '/%s/%s/%s' % (tl, prog.url, MAINPAGE_VIEWS[tl])
    return context
