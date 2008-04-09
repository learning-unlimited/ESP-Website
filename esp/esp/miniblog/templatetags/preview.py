from django import template
from django.contrib.auth.models import User, AnonymousUser
from esp.datatree.models import DataTree
from esp.users.models import UserBit
from esp.db.models import Q
from esp.miniblog.models import Entry, AnnouncementLink
from django.core.cache import cache
import re
import datetime
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

            # First we ensure we have a user
            try:
                self.user = template.resolve_variable(self.user, context)
                if not isinstance(self.user, (User, AnonymousUser)):
                    raise template.VariableDoesNotExist("Requires a user object, recieved '%s'" % self.user)
            except template.VariableDoesNotExist:
                 raise template.TemplateSyntaxError, "%s tag requires first argument, %s, to be a User" % (tag, self.user)


            # Now we check the cache
            self.cache_key = 'miniblog_%s_%s' % (self.user.id, limit)

            retVal = cache.get(self.cache_key)

            if retVal is not None:
                context[self.var_name] = retVal
                return ''

            # And we get the result
            verb = DataTree.get_by_uri('V/Subscribe')
            
            models_to_search = [Entry, AnnouncementLink]
            results = []
            grand_total = 0
            overflowed = False
            for model in models_to_search:
                result = UserBit.find_by_anchor_perms(model, self.user, verb).order_by('-timestamp').filter(Q(highlight_expire__gte = datetime.datetime.now()) | Q(highlight_expire__isnull = True))
                total = result.count()

                if self.limit:
                    overflowed = ((total - self.limit) > 0)
                    result = result[:self.limit]
                else:
                    overflowed = False
                    result = result
                results += result
                grand_total += total

            map(str, result)

            retVal = {'announcementList': results,
                      'overflowed':       overflowed,
                      'total':            grand_total}

            if self.user.id is not None:
                # cache for only 1 hour if it's an actual user.
                cache.set(self.cache_key, retVal, 3600)
            else:
                cache.set(self.cache_key, retVal, 86400)

            context[self.var_name] = retVal
            
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
