from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Category(models.Model):
    """ A permissions category, associated with a node in a permissions tree.

    It will eventually contain more details about what permissions it holds/requires/etc. """
    temp_desc_str = models.TextField()
    def __str__(self):
        return str(self.temp_desc_str)
    
    class Admin:
        pass

class Subscription(models.Model):
    """ Allows a user to 'subscribe', to watch for e-mail notices from, a particular category; the EmailController workflow handles the logic to check for this """
    user = models.ForeignKey(User)
    category = models.ForeignKey(Category)

    def __str__(self):
        return str(self.user.username) + ': ' + str(self.category)

    class Admin:
        pass
    
class DatatreeNodeData(models.Model):
    """ The data associated with a node in a Datatree
    The goal was to keep the tree 'pure', and hang data off of it.
    This set of data is used by the Watchlist permissions; if Datatrees get used for different purposes, this class should probably be renamed, and possibly restructured. """
    title = models.CharField(maxlength=256)
    text_data = models.TextField(blank=True)
    file_data = models.FileField(upload_to='/esp/uploaded_data/', blank=True)
    category = models.ForeignKey(Category, blank=True, null=True)
    heirarchical_top_down = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Admin:
        pass

class IllegalTreeRefactor(Exception):
    """ Thrown if something breaks horrifically while refactoring a tree.
    This shouldn't currently be possible, but it's kept around for good measure. """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Datatree(models.Model):
    """ An implementation of a nested-sets data tree, with data associated with each node """
    rangestart = models.IntegerField(editable=False, default=0)
    rangeend = models.IntegerField(editable=False, default=1)
    parent = models.ForeignKey('self', null=True, blank=True)
    node_data = models.ForeignKey(DatatreeNodeData, null=True, blank=True)
    name = models.SlugField() # Node name; should be unique at any given level of the tree

    def is_root(self):
        """ Returns True if this node is the ROOT of a global tree, false otherwise """
        return (parent == None & name == "ROOT")

    def tree_decode(self, tree_nodenames):
        """ Given a list of nodes leading from the current node to a direct descendant, return that descendant """
        if tree_nodenames == []:
            return self
        else:
            filtered = self.children().filter(name=tree_nodenames[0])
            if filtered.count() != 1:
                raise NoSuchNodeException(tree_nodenames[0])
            else:
                filtered[0].tree_decode(tree_nodenames[1:])

    def tree_encode(self):
        """  Return a list of the nodes leading from the root of the current tree (as determined by is_root()) to """
        if self.is_root():
            return []
        else:
            return parent.append(self.name)
    
    def children(self):
        """ Returns a QuerySet of Datatrees of all children of this Datatree """
        return Datatree.objects.filter(parent__pk=self.id)

    def is_descendant(self, node):
        """ Return False if the specified node is not a descendant (child, child of a child, etc.) of this node, AND if the specified node is not this node """
        return (node.rangestart >= self.rangestart & node.rangeend <= self.rangeend)

    def is_antecedent(self, node):
        """ Return False if the specified node is not an antecedent (parent, parent of a parent, etc.) of the current node, AND if the specified node is not this node """
        return (node.rangestart <= self.rangestart & node.rangeend >= self.rangeend)

    def sizeof(self):
        """ Return the total capacity of this node, as a nested-set element """
        return self.rangeend - self.rangestart

    def move(self, newstart):
        """ Accepts an integer, as a location.  Moves the range of this nested-set node to start at this location; refactors the subtree if it is necessary to shift sub-node locations. """
        print "Moving..." + str(self)
        curr_size = self.sizeof()
        self.rangestart = newstart
        self.rangeend = self.rangestart + curr_size
        print str(self) + ' ' + str(newstart) + ' '
        super(Datatree, self).save()
        self.refactor()
        
    def __str__(self):
        """ Returns a string
        
        If we have any associated data, display it in our string representation; otherwise, don't. """
        try:
            return str(self.rangestart) + ' .. ' + str(self.rangeend) + ' <' + str(self.node_data) + '>'
        except Exception:
            return str(self.rangestart) + ' .. ' + str(self.rangeend)

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

    def resize(self, newsize):
        """ Resize the nested-set range for this node; refactor this tree's parent if we don't have enough room to do that """
        self.rangeend = self.rangestart + newsize
        super(Datatree, self).save()
        if self.parent != None and self.parent != self:
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

    class Admin:
        pass

    # aseering: Including this line seems to break things badly, but excluding it makes node refactors unsafe
#    @transaction.commit_on_success
    def save(self):
        """ Save this node to the tree.

        If this node is its own parent, set its parent to 'None'.
        If this node doesn't fit into the tree that it's being saved into, refactor that tree to make it fit."""
        print "Saved"
        # Ugly hack to prevent loop trees
        if self.parent == self:
            self.parent = None
            
        super(Datatree, self).save()
        t = self.parent
        if t != None and t != self:
            if t.space_available_after(self) < self.sizeof():
                t.refactor()
        else:
            self.refactor()

class NoSuchNodeException(Exception):
    """ Raised if a required node in a Datatree doesn't exist """
    def __init__(self, value):
        self.value = "No such node: " + str(value)    

    def __str__(self):
        return repr(self.value)

class NoRootNodeException(NoSuchNodeException):
    """ The Datatree must always contain a node named 'ROOT', with no parent.  Raise this exception \
    if this is encountered. """
    def __init__(self):
        self.value = "No ROOT node in the Datatree"

def StringToPerm(permstr):
    """ Given a list of Slugs whose names trace from the tree Root to  """
    root_nodes = Datatree.objects.filter(parent=None,name="ROOT")
    if root_nodes.count() != 1:
        raise NoRootNodeException()

    root_node = root_node[0]

    return root_node.tree_decode(permstr.split('/'))

def PermToString(perm):
    return "/".join(perm.tree_encode())


# aseering: Dummy class, to be played with if/when Django subclassing works again.
# In the meantime, it's not in use.
class SubTree(Datatree):
    class Admin:
        pass


def GetNode(nodename):
    """ Get a Datatree node with the given slug; create it if it doesn't exist

    Return a QuerySet of nodes if more than one exists.
    """
    nodes = Datatree.objects.filter(name=nodename)
    if nodes.count < 1:
        node = Datatree()
        node.name = nodename
        node.save()
        return node
    elif nodes.count == 1:
        return nodes[0]
    else:
        return nodes
    
def PopulateInitialDatatree():
    """ Populate the Datatree with values for the ESP site heirarchy:

    ROOT
     |- UserGroupTree
     |- SiteTree
    """
    ROOT = GetNode('ROOT')
    UserGroupTree = GetNode('UserGroupTree')
    SiteTree = GetNode('SiteTree')

    # aseering 6-25-2006: Write check to see if any are QuerySets

    ROOT.parent = None
    UserGroupTree.parent = ROOT
    SiteTree.parent = ROOT

    UserGroupTree.save()
    SiteTree.save()
    ROOT.save()

    ROOT.refactor()
    
