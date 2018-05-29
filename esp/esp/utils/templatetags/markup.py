"""Filter to convert text to markdown

Copied and simplified for our use case from the Django 1.4 version of the
django.contrib.markup app:
  https://github.com/django/django/blob/stable/1.4.x/django/contrib/markup/templatetags/markup.py
This app has been deprecated by Django for security reasons.
However, we still need to use it with higher versions of Django,
and we are not as concerned about security since the Markdown code
is only entered by "trusted" users.  The code is also simpler for us since we
pin to a given version of markdown, and don't use markdown extensions.
"""

from django import template
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe

# Can't conflict with the `markdown` filter name.
import markdown as md

register = template.Library()


@register.filter(is_safe=True)
def markdown(value):
    """Runs Markdown over a given value."""
    return mark_safe(md.markdown(force_unicode(value)))
