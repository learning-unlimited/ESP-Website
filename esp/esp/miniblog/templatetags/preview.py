import re

from django import template
from django.contrib.auth.models import User, AnonymousUser

from esp.miniblog.views import get_visible_announcements

__all__ = ['MiniblogNode', 'miniblog_for_user']

arg_re = [
    (re.compile('\s*(\S+)\s+as\s+(\S+)\s+(\S+)\s+(\d+)\s*'), ('user', 'var_name', 'tl', 'limit')),
    (re.compile('\s*(\S+)\s+as\s+(\S+)\s+(\d+)\s*'), ('user', 'var_name', 'limit')),
    (re.compile('\s*(\S+)\s+as\s+(\S+)\s+(\S+)\s*'), ('user', 'var_name', 'tl')),
    (re.compile('\s*(\S+)\s+as\s+(\S+)\s*'), ('user', 'var_name')),
]

register = template.Library()

class MiniblogNode(template.Node):
    def __init__(self, user, var_name, limit = None, tl = None):
        self.limit = limit
        self.var_name = var_name
        self.user = user
        self.tl = tl

    def render(self, context):
        # First we ensure we have a user
        try:
            user_obj = template.Variable(self.user).resolve(context)
        except template.VariableDoesNotExist:
            if self.user == "AnonymousUser":
                user_obj = AnonymousUser()
            else:
                raise template.VariableDoesNotExist, "Argument to miniblog_for_user, %s, did not exist" % self.user
        if not isinstance(user_obj, (User, AnonymousUser)):
            raise template.TemplateSyntaxError("Requires a user object, recieved '%s'" % user_obj)

        context[self.var_name] = get_visible_announcements(user_obj, self.limit, self.tl)
        return ''

def parse_from_re(token, matching_rules):

    tag = token.contents.split()[0]
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % tag_name

    match = None
    for rule in matching_rules:
        match = rule[0].match(arg)
        if match:
            return dict( zip( rule[1], match.groups() ) )

    raise template.TemplateSyntaxError, "%r tag could not parse arguments" % tag_name


@register.tag
def miniblog_for_user(parser, token):
    """
    Returns a list of publicly-visible miniblog objects.

    E.g.
    {% miniblog_public tl as entries 5 %}
    will return the last 5 miniblog entries in the section tl
    as the context variable entries.
    """

    kwargs = parse_from_re(token, arg_re)
    if 'limit' in kwargs:
        try:
            kwargs['limit'] = int( kwargs['limit'] )
        except ValueError:
            raise template.TemplateSyntaxError, "miniblog_for_user tag requires limit argument to be an int"
    return MiniblogNode( **kwargs )
