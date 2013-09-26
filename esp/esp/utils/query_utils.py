from django.db.models.query_utils import Q
from django.utils.tree import Node
from django.db.models.sql.constants import LOOKUP_SEP

from copy import deepcopy

def shallow_copy_Q(q_object):
    obj = Node(connector=q_object.connector, negated=q_object.negated)
    obj.__class__ = q_object.__class__
    obj.children = q_object.children
    obj.subtree_parents = q_object.subtree_parents
    return obj
    
def append_to_child(child, root):
    if root and isinstance(child, tuple) and len(child)==2 and isinstance(child[0], basestring):
        return (root + LOOKUP_SEP + child[0], child[1])
    elif isinstance(child, Q):
        return nest_Q(child, root)
    else:
        return deepcopy(child)

def nest_Q(q_object, root=''):
    obj = shallow_copy_Q(q_object)
    obj.children = [append_to_child(child, root) for child in q_object.children]
    return obj

