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


def _module_page_registration(context):
    """Shared request lookup for the registration_checklist tag below.

    Reads ``request.program`` and ``request.tl`` (both set by the standard
    ESP view decorators) and returns ``(request, program, tl, options)``,
    where options is the StudentClassRegModuleInfo or ClassRegModuleInfo for
    the tl.  Returns None when there is no request, program or registration
    options, or the tl is not 'learn' or 'teach'.
    """
    request = context.get('request')
    if request is None:
        return None

    program = getattr(request, 'program', None)
    tl = getattr(request, 'tl', None)

    if program is None or tl not in ('learn', 'teach'):
        return None

    try:
        if tl == 'learn':
            options = program.studentclassregmoduleinfo
        else:
            options = program.classregmoduleinfo
    except (AttributeError, ObjectDoesNotExist):
        return None

    return request, program, tl, options


@register.simple_tag(takes_context=True)
def registration_checklist(context):
    """Return the checklist context used by module_base.html.

    Reuses ``checklist`` from the template context when the view already
    built it (as the registration main pages do); otherwise looks it up for
    the current student or teacher module page.  Returns an empty dict
    outside registration, so templates shared with other pages render as
    plain pages there.

    Also sets ``show_list`` (whether there is a checklist or other
    requirements to list), ``in_theme_sidebar`` (whether that list goes in
    the theme's own sidebar, per the theme's checklist_in_sidebar setting),
    ``lock_links`` (whether steps are shown without links) and, with the
    list, ``progress`` (see get_checklist_progress).
    The result is cached for the rest of the render, because
    module_base.html calls this from both its sidebar_extra and content
    blocks.
    """
    if 'registration_checklist' in context.render_context:
        return context.render_context['registration_checklist']

    # A view can pass an empty checklist to show none.
    checklist = context['checklist'] if 'checklist' in context else _lookup_checklist(context)
    if checklist:
        show_steps = checklist['options'].show_checklist
        checklist['show_steps'] = show_steps
        checklist['show_list'] = show_steps or bool(checklist.get('records'))
        checklist['in_theme_sidebar'] = checklist['show_list'] and _theme_has_checklist_sidebar(context)
        if checklist['show_list']:
            checklist['progress'] = get_checklist_progress(checklist, include_steps=show_steps)
        # Until the required modules are done, findModule sends the user
        # through them in order, so the checklist shouldn't link around that.
        checklist['lock_links'] = (not checklist['completedAll']
                                   and _forces_required_modules(checklist['program']))

    context.render_context['registration_checklist'] = checklist
    return checklist


def _forces_required_modules(program):
    """True if registration makes users complete required modules in order."""
    try:
        return program.studentclassregmoduleinfo.force_show_required_modules
    except (AttributeError, ObjectDoesNotExist):
        return False


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


def _lookup_checklist(context):
    """Checklist context for the current registration module page, or an empty dict."""
    registration = _module_page_registration(context)
    if registration is None:
        return {}
    request, program, tl, options = registration

    if not request.user.is_authenticated:
        return {}

    checklist = get_module_page_checklist_context(request.user, program, tl)
    checklist['options'] = options
    return checklist
