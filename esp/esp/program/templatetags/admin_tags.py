from django import template

register = template.Library()

@register.inclusion_tag('program/modules/admin_config_banner.html', takes_context=True)
def admin_config_banner(context, config_url, link_text=None):
    """
    Renders a staff-only banner linking admins to the configuration
    page for the current form. Only visible to logged-in staff users.
    Hidden from regular users and in print views.

    Usage:
        {% load admin_tags %}
        {% admin_config_banner config_url="/manage/some/url/" %}
        {% admin_config_banner config_url="/manage/some/url/" link_text="Edit this form" %}

    Issue: #3690
    """
    request = context.get('request')

    is_staff = (
        request is not None
        and hasattr(request, 'user')
        and request.user.is_authenticated
        and request.user.is_staff
    )

    if not is_staff:
        return {'show_banner': False}

    return {
        'show_banner': True,
        'config_url': config_url,
        'link_text': link_text or 'Want to edit this form? Click here to configure it.',
    }