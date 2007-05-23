from django import template
from django.contrib.auth.models import User, AnonymousUser
from esp.datatree.models import DataTree
from esp.users.models import UserBit
from esp.miniblog.models import Entry
import re

arg_re_num = re.compile('\s*(\S+)\s+as\s+(\S+)\s+(\d+)\s*')
arg_re     = re.compile('\s*(\S+)\s+as\s+(\S+)\s*')

register = template.Library()

@register.tag
def miniblog_for_user(parser, token):
    """
    Returns a list of miniblog objects for a particular node.

    E.g.
    {% preview_miniblog user_obj as entries 5 %}
    will return the last 5 miniblog entries attached to the user user_obj
    as the context variable entries.
    """

    class MiniblogNode(template.Node):
        def __init__(self, user, var_name, limit = None):
            self.limit = limit
            self.var_name = var_name
            self.user = user

        def render(self, context):
            verb = DataTree.get_by_uri('V/Subscribe')

            try:
                self.user = template.resolve_variable(self.user, context)
                if not isinstance(self.user, (User, AnonymousUser)):
                    raise template.VariableDoesNotExist("Requires a user object, recieved '%s'" % self.user)
            except template.VariableDoesNotExist:
                 raise template.TemplateSyntaxError, "%s tag requires first argument, %s, to be a User" % (tag, self.user)

            result = UserBit.find_by_anchor_perms(Entry, self.user, verb).order_by('-timestamp')

            total = result.count()

            if self.limit:
                overflowed = ((total - self.limit) > 0)

                result = result[:self.limit]
            else:
                overflowed = False
                result = result

            context[self.var_name] = {'announcementList': result,
                                      'overflowed':       overflowed,
                                      'total':            total}
            
            return ''

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
