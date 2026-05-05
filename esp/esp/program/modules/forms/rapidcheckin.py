"""Form widget for rapid check-in student field: renders inputs only (no autocomplete script).

The template ajaxcheckin.html initializes jQuery UI autocomplete with filter-aware
source (grade, last_name_range, prog) so the widget must not inject its own script.
"""
from django import forms
from django.utils.safestring import mark_safe
from django.template.defaultfilters import addslashes

from esp.users.models import ESPUser


class RapidCheckinStudentWidget(forms.Widget):
    """Renders the target_user text + hidden inputs only. No script."""

    def __init__(self, attrs=None, *args, **kwargs):
        super().__init__(attrs, *args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        init_val = ""
        data = ""
        if value is not None and value != "":
            try:
                user = ESPUser.objects.get(pk=int(value))
                init_val = user.ajax_str() + " (%s)" % value
                data = str(value)
            except (ESPUser.DoesNotExist, ValueError, TypeError):
                pass
        html = (
            '<input type="text" id="id_%s" name="%s_raw" value="%s" class="span6" />'
            % (name, name, addslashes(init_val))
        )
        html += '<input type="hidden" id="id_%s_data" name="%s" value="%s" />' % (
            name,
            name,
            addslashes(data),
        )
        return mark_safe(html)
