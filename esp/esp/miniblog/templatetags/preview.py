"""Compatibility template tags for legacy theme preview blocks.

Some older theme templates load a `preview` library and call
`miniblog_for_user`. The original miniblog implementation was removed, but
those templates still need a lightweight object to render safely.
"""

from dataclasses import dataclass, field

from django import template
from django.template import TemplateSyntaxError

register = template.Library()


@dataclass
class AnnouncementCollection:
    """Shape expected by legacy templates."""

    announcementList: list = field(default_factory=list)
    overflowed: bool = False


class MiniblogForUserNode(template.Node):
    def __init__(self, context_var):
        self.context_var = context_var

    def render(self, context):
        # Provide an empty collection so templates can render without errors.
        context[self.context_var] = AnnouncementCollection()
        return ""


@register.tag(name="miniblog_for_user")
def miniblog_for_user(parser, token):
    """Parse legacy forms like:

    {% miniblog_for_user AnonymousUser as announcements teach 3 %}
    {% miniblog_for_user user teach 3 as announcements %}
    """

    bits = token.split_contents()
    if len(bits) < 4:
        raise TemplateSyntaxError(
            "miniblog_for_user requires at least a user expression and an 'as <var>' clause"
        )

    if "as" not in bits:
        raise TemplateSyntaxError("miniblog_for_user requires 'as <var>'")

    as_index = bits.index("as")
    if as_index == len(bits) - 1:
        raise TemplateSyntaxError("miniblog_for_user missing variable name after 'as'")

    context_var = bits[as_index + 1]
    return MiniblogForUserNode(context_var)
