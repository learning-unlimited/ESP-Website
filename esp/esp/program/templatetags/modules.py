from django import template
from django.core.exceptions import ObjectDoesNotExist

from esp.program.modules.checklist import get_checklist_progress, get_module_page_checklist_context
from esp.themes.controllers import ThemeController

register = template.Library()


@register.filter
def hasModule(program, module):
    """True if the program has the given module.  False otherwise, or if the
    program is None."""
    if program is None:
        return False
    else:
        return program.hasModule(module)


def _module_page_registration(context, tls=('learn', 'teach')):
    """Shared request lookup for the module page checklist tags below.

    Reads ``request.program`` and ``request.tl`` (both set by the standard
    ESP view decorators) and returns ``(request, program, tl, scrmi)``, where
    scrmi is the StudentClassRegModuleInfo or ClassRegModuleInfo for the tl.
    Returns None when there is no request, program or registration options,
    or the tl is not in ``tls``.
    """
    request = context.get('request')
    if request is None:
        return None

    program = getattr(request, 'program', None)
    tl = getattr(request, 'tl', None)

    if program is None or tl not in tls:
        return None

    try:
        if tl == 'learn':
            scrmi = program.studentclassregmoduleinfo
        else:
            scrmi = program.classregmoduleinfo
    except (AttributeError, ObjectDoesNotExist):
        return None

    return request, program, tl, scrmi


@register.inclusion_tag('program/modules/module_progress.html', takes_context=True)
def registration_progress(context):
    """Render the registration checklist or progress bar on a module page.

    Looks up the full list of modules and computes completion state, then
    passes them to ``module_progress.html`` so the existing
    checkboxes/progressbar partials can render without changes.

    Returns an empty dict (renders nothing) when:
      - there is no request in the template context, or
      - the current tl is not 'learn' or 'teach', or
      - the progress_mode for this registration type is 0 (disabled).
    """
    registration = _module_page_registration(context)
    if registration is None:
        return {}
    request, program, tl, scrmi = registration

    if scrmi.progress_mode == 0:
        return {}

    if not request.user.is_authenticated:
        return {}

    checklist = get_module_page_checklist_context(request.user, program, tl)
    checklist['scrmi'] = scrmi
    return checklist


@register.simple_tag(takes_context=True)
def teacher_checklist(context):
    """Return the checklist context used by teacher_module_base.html.

    Reuses ``checklist`` from the template context when the view already
    built it (as the teacher registration main page does); otherwise looks it
    up for the current teacher module page.  Returns an empty dict outside
    teacher registration, so templates shared with other pages render as
    plain pages there.

    Also sets ``show_list`` (whether there is a checklist or other
    requirements to list), ``in_theme_sidebar`` (whether that list goes in
    the theme's own sidebar, per the theme's checklist_in_sidebar setting)
    and, with the list, ``progress`` (see get_checklist_progress).
    The result is cached for the rest of the render, because
    teacher_module_base.html calls this from both its sidebar_extra and content
    blocks.
    """
    if 'teacher_checklist' in context.render_context:
        return context.render_context['teacher_checklist']

    checklist = context.get('checklist') or _lookup_teacher_checklist(context)
    if checklist:
        show_steps = checklist['options'].progress_mode == 1
        checklist['show_list'] = show_steps or bool(checklist.get('records'))
        checklist['in_theme_sidebar'] = checklist['show_list'] and _theme_has_checklist_sidebar(context)
        if checklist['show_list']:
            checklist['progress'] = get_checklist_progress(checklist, include_steps=show_steps)

    context.render_context['teacher_checklist'] = checklist
    return checklist


def _theme_has_checklist_sidebar(context):
    """True if the current theme is set to show the checklist in its sidebar.

    Only themes whose config form has a checklist_in_sidebar field (and whose
    main.html has a sidebar_extra block) support this.  The theme settings Tag
    keeps old keys when the theme changes, so the field is checked too.
    """
    tc = ThemeController()
    form_class = tc.get_config_form_class(tc.get_current_theme())
    if form_class is None or 'checklist_in_sidebar' not in form_class.base_fields:
        return False
    theme = context.get('theme') or tc.get_template_settings()
    return bool(theme.get('checklist_in_sidebar'))


def _lookup_teacher_checklist(context):
    """Checklist context for the current teacher module page, or an empty dict."""
    registration = _module_page_registration(context, tls=('teach',))
    if registration is None:
        return {}
    request, program, tl, crmi = registration

    if not request.user.is_authenticated:
        return {}

    checklist = get_module_page_checklist_context(request.user, program, tl)
    checklist['options'] = crmi
    return checklist
