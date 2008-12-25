from esp.datatree.decorators import branch_find
from django.http import Http404
from esp.miniblog.models import Entry
from django.db.models.query import Q

__all__ = ['miniblog_find']


def miniblog_find(method):

    @branch_find
    def _dec(request, node, name, section, action, *args, **kwargs):
        if section is None or section.strip() == '':
            all_list = Entry.objects.filter(Q(section__isnull = True) |
                                            Q(section = ''))
        else:
            all_list = Entry.objects.filter(section = section)

#        assert False, name

        try:
            entry = all_list.get(anchor = node,
                                 slug   = name)
        except:
            raise Http404

        return method(request, entry, action, *args, **kwargs)

    _dec.__doc__ = method.__doc__

    return _dec
