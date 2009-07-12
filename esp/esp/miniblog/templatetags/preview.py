import re

from django import template
from django.contrib.auth.models import User, AnonymousUser
from django.db.models.query import Q

from esp.datatree.models import *
from esp.miniblog.views import get_visible_announcements

__all__ = ['MiniblogNode', 'miniblog_for_user']

arg_re_num = re.compile('\s*(\S+)\s+as\s+(\S+)\s+(\d+)\s*')
arg_re     = re.compile('\s*(\S+)\s+as\s+(\S+)\s*')

register = template.Library()

class MiniblogNode(template.Node):
    def __init__(self, user, var_name, limit = None):
        self.limit = limit
        self.var_name = var_name
        self.user = user

    def render(self, context):

        # First we ensure we have a user
        try:
            user_obj = template.resolve_variable(self.user, context)
        except template.VariableDoesNotExist:
             raise template.VariableDoesNotExist, "Argument to miniblog_for_user, %s, did not exist" % self.user
        if not isinstance(user_obj, (User, AnonymousUser)):
            raise template.TemplateSyntaxError("Requires a user object, recieved '%s'" % user_obj)

        context[self.var_name] = get_visible_announcements(user_obj, self.limit)
        return ''


@register.tag
def miniblog_for_user(parser, token):
    """
    Returns a list of miniblog objects for a particular node.

    E.g.
    {% preview_miniblog user_obj as entries 5 %}
    will return the last 5 miniblog entries attached to the user user_obj
    as the context variable entries.
    """


    tag = token.contents.split()[0]
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % tag

    match = arg_re_num.match(arg)
    if match:
        user, var_name, limit = match.groups()
    else:
        limit = None
        match = arg_re.match(arg)
        if not match:
            raise template.TemplateSyntaxError, "%r tag requires at least two arguments" % tag
        user, var_name = match.groups()

    if limit:
        try:
            limit = int(limit)
        except ValueError:
            raise template.TemplateSyntaxError, "%s tag requires third argument to be an int" % tag

    return MiniblogNode(user, var_name, limit)
