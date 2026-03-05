from django import template
from django.core.exceptions import ObjectDoesNotExist

register = template.Library()


@register.filter
def hasModule(program, module):
    """True if the program has the given module.  False otherwise, or if the
    program is None."""
    if program is None:
        return False
    else:
        return program.hasModule(module)


@register.inclusion_tag('program/modules/module_progress.html', takes_context=True)
def registration_progress(context):
    """Render the registration checklist or progress bar on a module page.

    Reads ``request.program`` and ``request.tl`` (both set by the standard
    ESP view decorators) to look up the full list of modules and compute
    completion state, then passes them to ``module_progress.html`` so the
    existing checkboxes/progressbar partials can render without changes.

    Returns an empty dict (renders nothing) when:
      - there is no request in the template context, or
      - the current tl is not 'learn' or 'teach', or
      - the progress_mode for this registration type is 0 (disabled).
    """
    request = context.get('request')
    if request is None:
        return {}

    program = getattr(request, 'program', None)
    tl = getattr(request, 'tl', None)

    if program is None or tl not in ('learn', 'teach'):
        return {}

    try:
        if tl == 'learn':
            scrmi = program.studentclassregmoduleinfo
        else:
            scrmi = program.classregmoduleinfo
    except (AttributeError, ObjectDoesNotExist):
        return {}

    if scrmi.progress_mode == 0:
        return {}

    modules = program.getModules(request.user, tl)

    completedAll = not any(
        not m.isCompleted() and m.isRequired()
        for m in modules
    )

    extra_steps = {'learn': 'learn:extra_steps', 'teach': 'teach:extra_steps'}.get(tl)

    return {
        'modules': modules,
        'scrmi': scrmi,
        'completedAll': completedAll,
        'program': program,
        'extra_steps': extra_steps,
        'is_module_page': True,
    }
