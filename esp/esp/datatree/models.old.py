
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from django.db import models
from django.contrib.auth.models import User, AnonymousUser
from django.core.cache import cache
from django.db.models.query import Q
from django.template.defaultfilters import urlencode
from esp.middleware import ESPError

# Create your models here.
    
def StringToPerm(permstr):
    """ Convert a permission from 'a/b/c' format to [a, b, c] format """
    return permstr.split('/')

def PermToString(perm):
    """ Convert a permission from [a, b, c] format to 'a/b/c' format """
    if perm == []:
        return ''
    else:
        return "/".join(perm)

class DataTree(models.Model):
    """ An implementation of a nested-sets data tree, with data associated with each node """
    rangestart = models.IntegerField(editable=False, default=0)
    rangeend = models.IntegerField(editable=False, default=1)
    parent = models.ForeignKey('self', null=True, blank=True)
    name = models.SlugField() # Node name; should be unique at any given level of the tree
    friendly_name = models.CharField(max_length=256,blank=True)

    def tree_decode(self, tree_nodenames):
        """ Given a list of nodes leading from the current node to a direct descendant, return that descendant """

        if tree_nodenames == []:
            return self
        else:
            filtered = self.children().filter(name=tree_nodenames[0])
            length = len(filtered)

            if length < 1:
                raise self.NoSuchNodeException(self,tree_nodenames)
            elif length > 1:
                raise self.DuplicateNodeException(self,tree_nodenames)
            else:
                return filtered[0].tree_decode(tree_nodenames[1:])



    def tree_create(self, tree_nodenames):
        """ Given a list of nodes leading from the current node to a direct descendant, return that descendant, creating it if it does not exist """
        # This is blatant code copying from tree_decode(); anyone know
        # of a good way to rewrite one based on the other?
        if tree_nodenames == []:
            return self
        else:
            filtered = self.children().filter(name=tree_nodenames[0])
            if filtered.count() < 1:
                newnode = DataTree()
                newnode.parent = self
                newnode.name = tree_nodenames[0]
                newnode.save()

                self.refactor()

                return newnode.tree_create(tree_nodenames[1:])
                
            elif filtered.count() > 1:
                raise self.DuplicateNodeException(self,tree_nodenames)
            else:
                return filtered[0].tree_create(tree_nodenames[1:])

    def tree_encode(self):
        """  Return a list of the nodes leading from the root of the current tree (as determined by is_root()) to """
        if self.parent == None:
            return []
        else:
            stack = self.parent.tree_encode()
            stack.append(self.name) 
            return stack

    def depth(self):
        return len(self.tree_encode())
    
    def children(self):
        """ Returns a QuerySet of DataTrees of all children of this DataTree """
        return DataTree.objects.filter(parent__pk=self.id)

    def Q_descendants(self):
        """ Return a 'Q' object that, when passed to a Django filter on a DataTree node, will filter for all descendants of the current node """
        return Q(rangestart__gte=self.rangestart, rangeend__lte=self.rangeend)

    
    def is_descendant(self, node):
        """ Return False if the specified node is not a descendant (child, child of a child, etc.) of this node, AND if the specified node is not this node """
        return (node.rangestart >= self.rangestart and node.rangeend <= self.rangeend)

    def Q_antecedents(self):
        """ Return a 'Q' object that, when passed to a Django filter on a DataTree node, will filter for all descendants of the current node """
        return Q(rangestart__lte=self.rangestart, rangeend__gte=self.rangeend)

    def descendants(self, distinct = True):
        """ Return a QuerySet of all descendants."""
        return self.descendants_nocache(distinct)

    def descendants_nocache(self, distinct = True):
        """ Return a QuerySet of all descendants."""
        QSet =  DataTree.objects.filter(self.Q_descendants())
        if distinct:
            return QSet.distinct()
        else:
            return QSet

    def antecedents(self, distinct = True):
        """ Return a QuerySet of all antecedents."""
        return self.antecedents_nocache(distinct)
    
    def antecedents_nocache(self, distinct = True):
        """ Return a QerySet of all antecedents."""
        QSet = DataTree.objects.filter(self.Q_antecedents())
        if distinct:
            return QSet.distinct()
        else:
            return QSet
    
    def is_antecedent(self, node):
        """ Return False if the specified node is not an antecedent (parent, parent of a parent, etc.) of the current node, AND if the specified node is not this node """
        return (node.rangestart <= self.rangestart and node.rangeend >= self.rangeend)

    def sizeof(self):
        """ Return the total capacity of this node, as a nested-set element """
        return self.rangeend - self.rangestart

    def move(self, newstart):
        """ Accepts an integer, as a location.  Moves the range of this nested-set node to start at this location; refactors the subtree if it is necessary to shift sub-node locations. """
        curr_size = self.sizeof()
        self.rangestart = newstart
        self.rangeend = self.rangestart + curr_size
        super(DataTree, self).save()
        self.refactor()
        
    def full_name(self):
        """ Returns the full, slash-delimited name of a node """
        return ( '/'.join(self.tree_encode()))

    def __unicode__(self):
        """ Returns a string """
	#res = str(self.rangestart) + ' .. ' + str(self.rangeend) + ' '*self.depth() + ' <' + str(self.full_name()) + '>'
        res = str(self.full_name()) 
	
	return res

    def total_size_of_children(self):
        """ Return the total nested-set size of all subnodes.  Should, in theory, always be less than self.sizeof(). """
        total_size=0
        for child in self.children():
            total_size += child.sizeof()
        return total_size

    def refactor(self):
        """ Rearrange the nested-set values, to make the tree 'correct', with enough space to add nodes.  This function is recursive down the tree. """
        # Cache a bunch of variables; these may change, and I want to be able to use their initial values
        childsize = self.total_size_of_children()
        selfsize = self.sizeof()
        curr_children = self.children()
        numchildren = curr_children.count()

        # Leave one unit free for this node, so that the rangestart values can be unique
        # If we're out of space at this node, fix this.
        if childsize > selfsize - 1:
            self.resize(childsize + selfsize + 1)


        # If we don't have any children, don't continue; all future code deals with recursing through children and making space for, or refactoring, them
        if numchildren == 0:
            return

        # Space nodes evenly in the available space; if the spacing for this is nonintegral, make it integral and accumulate the difference at the end of the available space range
        spacing = int( (selfsize - childsize) / numchildren )

        curr_location = self.rangestart + 1

        # Move all children as needed
        for child in curr_children:
            child.move(curr_location)
            curr_location += child.sizeof() + spacing

    def rcopy(self, other, first=True):
        """ Recursively copy datatree branches from one section to the next.
            Example: foo = GetNode('V')
                     foo.rcopy(GetNode('v2')
            Now everything in 'V'is copied to live in 'V2' """
        # we have no children, return
        if self.children().count() == 0:
            return

        # let's resize
        other.resize(self.sizeof(), False)

        #get a list of all descendents
        proper_descendants =  list(self.descendants().exclude(id = self.id).order_by('parent'))
        new_descendants = []
        
        for child in self.children():
            # Create the child node
            
            other_child, created = DataTree.objects.get_or_create(parent = other.id,
                                                                  name   = child.name)
            
            other_child.friendly_name = child.friendly_name
            models.Model.save(other_child)

            # recursive...
            child.rcopy(other_child)

        # return the other node
        if first:
            # since refactor() is recursive, we'll refactor at the end of the day.
            other.refactor()
            return other

        return None
    
    

    def resize(self, newsize, refactor = True):
        """ Resize the nested-set range for this node; refactor this tree's parent if we don't have enough room to do that """
        self.rangeend = self.rangestart + newsize
        super(DataTree, self).save()
        if self.parent != None and self.parent != self and refactor:
            self.parent.refactor()

    def autoenlarge(self):
        """ Automatically enlarge the current nested-set range to the 'correct' size """
        self.resize(self.sizeof()*2)

    def space_available_after(self, node):
        """ Returna an integer

        Given a node, returns the space available between the end of that node and the start of the next node. """
        min_start = node.rangeend

        for child in self.children():
            if node.rangestart < child.rangestart:
                min_start = min(child.rangestart, min_start)

        return node.rangeend - min_start


    def __getitem__(self, key):
        """ A hook to get the children of a node. """
        import exceptions
        try:
            return self.tree_decode([key])
        except:
            raise exceptions.KeyError, key

    def keys(self):
        return [ x.name for x in self.children() ]

    def items(self):
        return [ (x.name, x) for x in self.children() ]

    values = children

    def __setitem__(self, key, value):
        """ A hook to reset the value of a key. """
        if type(value) != DataTree:
            assert False, 'Invalid data type! Expected data tree'

        try:
            other_child = DataTree.objects.get(parent = self,
                                               name = key)
            other_child.friendly_name = value.friendly_name
            other_child.save()
            return other_child
        except:
            value.name = key
            value.parent = self
            value.save()

    def __len__(self):
        return self.descendants().count()

    def has_key(self, key):
        return self.children().filter(name__exact = key).count() > 0

    def __contains__(self, child):
        ' Returns true if the child is underneath self. '
        if type(child) != DataTree:
            return False

        return self.descendants().filter(id = child.id).count() > 0

    class Admin:
        pass

    class Meta:
	    ordering = ['rangestart']

    def delete(self, recurse = False, superDelete = False):
        """ Delete this tree node.
            If you call node.delete() and this node has children,
            it will result in an error. Please call:
            node.delete(recurse=True) or node.delete(True) to delete
            recursively."""
        # we're going to bypass this entirely
        if superDelete:

            return super(DataTree, self).delete()

        # if we are not overriding and we have children
        if not recurse and self.children().count() > 0:
            assert False, 'Cannot delete this node--it has children!'

        # if we are overriding we're going to deleve all subnodes
        if self.children().count() > 0:
            for child in self.descendants():
                child.delete(superDelete = True)
            return None
        
        super(DataTree, self).delete()

    # aseering: Including this line seems to break things badly, but excluding it makes node refactors not thread-safe
#    @transaction.commit_on_success
    def save(self):
        """ Save this node to the tree.

        If this node is its own parent, set its parent to 'None'.
        If this node doesn't fit into the tree that it's being saved into, refactor that tree to make it fit."""
        # Ugly hack to prevent loop trees
        if self.parent == self:
            self.parent = None
            
        super(DataTree, self).save()
        t = self.parent
        if t != None and t != self:
            if t.space_available_after(self) < self.sizeof():
                t.refactor()
                self.refactor()
        else:
            self.refactor()

    class IllegalTreeRefactor(Exception):
	    """ Thrown if something breaks horrifically while refactoring a tree.
	    This shouldn't currently be possible, but it's kept around for good measure. """
	    def __init__(self, value):
	        self.value = value
	    def __unicode__(self):
	        return repr(self.value)

    class NoSuchNodeException(Exception):
        """ Raised if a required node in a DataTree doesn't exist """
        def __init__(self, anchor, remainder):
	    self.anchor = anchor
	    self.remainder = remainder

        def __unicode__(self):
            return "Node not found: " + repr(self.remainder[0])

    class DuplicateNodeException(Exception):
	    """ Raised if trying to traverse a DataTree with ambiguous child names """
	    def __init__(self, value, anchor):
		    self.value = "duplicate node: " + str(value)
		    self.anchor = anchor
	    def __unicode__(self):
		    return repr(self.value)

    class NoRootNodeException(NoSuchNodeException):
        """ The DataTree must always contain a node named 'ROOT', with no parent.  Raise this exception \
        if this is encountered. """
        def __init__(self, NumOfRootNodes):
           DataTree.NoSuchNodeException.__init__(self, None, ['ROOT'])
           self.value = str(NumOfRootNodes) + " ROOT nodes in the DataTree"
	def __unicode__(self):
		return repr(self.value)

def GetNode(nodename):
    """ Get a DataTree node with the given path; create it if it doesn't exist """
    # aseering 12-15-2006: Cache query results.  Pull them from the cache when possible.
    cache_id = 'datatree:' + nodename

    cached_val = cache.get(urlencode(cache_id))
    if cached_val != None:
        return cached_val

    nodes = DataTree.objects.filter(name='ROOT', parent__isnull=True)
    node = None
    if nodes.count() < 1L:
        error("Trying to create a new root node.  Dying here.")
        assert False, "Trying to create a new root node.  Dying here."
        node = DataTree()
        node.name = 'ROOT'
        node.parent = None
        node.save()
    elif nodes.count() == 1L:
        node = nodes[0]
    else:
	#node = nodes[0]
        raise DataTree.NoRootNodeException(nodes.count())

    perm = StringToPerm(nodename)
    if nodename == '':
        perm = []
        
    # aseering 12-15-2006: Encache output
    retVal = node.tree_create(perm)

    # aseering 1-11-2006: Quick'n'dirty hack to force the node to get evaluated
    if retVal.id == -1:
        pass
    
    cache.set(urlencode(cache_id), retVal)
    return retVal


    

