"""
Reusable template tags for the Onsite Admin Dashboard.
Provides inclusion tags for common UI components.
"""

from django import template

register = template.Library()


@register.inclusion_tag('inclusion/program/onsite_admin/stat_card.html')
def render_stat_card(number, label, card_id=''):
    """Render a summary statistic card.

    Args:
        number: The statistic value to display
        label: The label/description for the stat
        card_id: Optional ID for dynamic updates via JavaScript
    """
    return {
        'number': number,
        'label': label,
        'card_id': card_id,
    }


@register.inclusion_tag('inclusion/program/onsite_admin/progress_bar.html')
def render_enrollment_progress(enrolled, attending, capacity):
    """Render dual progress bars showing enrollment and attendance.

    Args:
        enrolled: Number of enrolled students
        attending: Number of attending students
        capacity: Section capacity
    """
    enrolled_pct = (enrolled / capacity * 100) if capacity > 0 else 0
    attending_pct = (attending / capacity * 100) if capacity > 0 else 0

    # Determine status class based on enrollment percentage
    if enrolled_pct >= 100:
        status_class = 'progress-danger'
    elif enrolled_pct >= 75:
        status_class = 'progress-warning'
    else:
        status_class = ''

    return {
        'enrolled': enrolled,
        'attending': attending,
        'capacity': capacity,
        'enrolled_pct': min(enrolled_pct, 100),
        'attending_pct': min(attending_pct, 100),
        'status_class': status_class,
    }


@register.inclusion_tag('inclusion/program/onsite_admin/section_status_badge.html')
def render_section_status(section):
    """Render status badges for a section (Open/Closed/Full).

    Args:
        section: ClassSection object or dict with is_reg_open and is_full
    """
    # Handle both ClassSection objects and dicts from JSON
    if isinstance(section, dict):
        is_reg_open = section.get('is_reg_open', False)
        is_full = section.get('is_full', False)
    else:
        is_reg_open = section.isRegOpen()
        is_full = section.isFull()

    if not is_reg_open:
        status_class = 'status-closed'
        status_text = 'Closed'
    elif is_full:
        status_class = 'status-full'
        status_text = 'Full'
    else:
        status_class = 'status-open'
        status_text = 'Open'

    return {
        'status_class': status_class,
        'status_text': status_text,
        'is_full': is_full,
    }


@register.inclusion_tag('inclusion/program/onsite_admin/class_card.html', takes_context=True)
def render_class_card(context, section):
    """Render a class card for the dashboard list.

    Args:
        context: Template context (provides program_url)
        section: ClassSection object with enrollment data
    """
    program_url = context.get('program', {})
    if hasattr(program_url, 'getUrlBase'):
        program_url = program_url.getUrlBase()

    return {
        'section': section,
        'program_url': program_url,
    }


@register.filter
def percentage(value, total):
    """Calculate percentage for template use.

    Usage: {{ enrolled|percentage:capacity }}
    """
    if not total or total == 0:
        return 0
    return min(int(value / total * 100), 100)
