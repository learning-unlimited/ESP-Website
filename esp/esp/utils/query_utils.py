from django.db.models.query_utils import Q
from django.utils.tree import Node
from django.db.models.constants import LOOKUP_SEP

from copy import deepcopy

def shallow_copy_Q(q_object):
    obj = Node(connector=q_object.connector, negated=q_object.negated)
    obj.__class__ = q_object.__class__
    obj.children = q_object.children
    return obj

def nest_Q(q_object, root=''):
    """
    Takes a Q object and a root, and prepends the root recursively to all conditions.

    For example, if
    q = Q(relationship__name="Enrolled", end_date__gte=datetime.now())
    then
    nest_Q(q, 'studentregistration')
    returns
    Q(studentregistration__relationship__name="Enrolled",
      studentregistration__end_date__gte=datetime.now())
    """
    obj = shallow_copy_Q(q_object)
    obj.children = [_append_to_child(child, root) for child in q_object.children]
    return obj

def _append_to_child(child, root):
    if root and isinstance(child, tuple) and len(child)==2 and isinstance(child[0], basestring):
        return (root + LOOKUP_SEP + child[0], child[1])
    elif isinstance(child, Q):
        return nest_Q(child, root)
    else:
        return deepcopy(child)

