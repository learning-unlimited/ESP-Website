"""Context helpers for the registration checklist (checkboxes.html and
progressbar.html), shared by the registration main pages and module pages."""

from esp.program.modules.handlers.studentregcore import StudentRegCore

MAINPAGE_VIEWS = {'learn': 'studentreg', 'teach': 'teacherreg'}


def get_checklist_context(user, prog, tl, modules=None):
    """Return the checklist context for ``user`` in the ``tl`` ('learn' or
    'teach') registration for ``prog``.

    Pass ``modules`` to reuse a list already fetched with prog.getModules().
    """
    if modules is None:
        modules = prog.getModules(user, tl)

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


def get_module_page_checklist_context(user, prog, tl):
    """Like get_checklist_context(), but for a module page other than the
    main page, so checklist links point back to the main page."""
    context = get_checklist_context(user, prog, tl)
    context['is_module_page'] = True
    context['mainpage_url'] = '/%s/%s/%s' % (tl, prog.url, MAINPAGE_VIEWS[tl])
    return context
