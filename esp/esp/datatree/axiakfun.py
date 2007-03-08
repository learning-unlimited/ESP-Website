from django.db import models
from django.db import transaction
import exceptions

class Tree(models.Model):
    " This model organizes the site into a tight heirarchy. "

    START_SIZE  = 2
    DELIMITER   = '/'
    ROOT_ID     = 1

    name        = models.CharField(maxlength=64)
    parent      = models.ForeignKey('self',blank=True,null=True)
    rangestart  = models.IntegerField()
    rangeend    = models.IntegerField()
    uri         = models.TextField()
    uri_correct = models.BooleanField(default = False)



    class Meta:
        # parent and name should be unique
        unique_together = (("name", "parent"),)

    class Admin:
        pass

    ########################
    # PARAMETER Functions  #
    ########################
    
    def expanded_size(self):
        " This is whatever the expanded size should be. "
        size = self.range_size()
        if size < 2:
            return 2
        else:
            return 2*size

    #######################
    # MUTATORS            #
    #######################
    def delete(self, recurse = False, superdelete = False):
        " Delete tree nodes. "
        if superdelete:
            return super(Tree, self).delete()

        # need these for later
        rangestart = self.rangestart
        rangeend   = self.rangeend

        if len(self) > 0:
            if not recurse:
                raise PermissionDenied, "You cannot delete a tree without deleting its children."
            
            self.delete_descendants()

        # move all of the tree nodes to the left.
        Tree.shift_many_ranges(rangestart,
                               rangestart - rangeend - 1)

        return super(Tree, self).delete()
        

    
    def save(self, create_root = False, uri_fix = False):
        # fall back to g'old save
        if self.id is not None and not create_root and not uri_fix:
            self.expire_uri()
            return super(Tree, self).save()
        
        if not create_root and self.parent is None:
            raise Tree.CannotCreateRootException, "You cannot create a root node."
        # if the parent is something
        if self.parent is not None:
            parent = self.parent
            # siblings ordered by their end range.
            siblings = parent.children().order_by('-rangeend')
            if siblings.count() > 0:
                upperbound = siblings[0].rangeend
            else:
                upperbound = parent.rangestart

            if parent.rangeend < (upperbound + Tree.START_SIZE):
                # we dont' have enough room...time to expand
                parent.expand()
                
            self.rangestart = upperbound + 1
            self.rangeend   = upperbound + Tree.START_SIZE
        else:
            self.rangestart = 0
            self.rangeend   = Tree.START_SIZE - 1
            # make room for this tree node
            Tree.shift_all_ranges(Tree.START_SIZE)
            
        return super(Tree, self).save()


    def expand(self):
        " Make this parent now have room."
        Tree.shift_many_ranges(self.rangeend,
                               self.expanded_size())


    ######################
    # ACCESSORS          #
    ######################
    def __str__(self):
        return '%s (%s--%s)' % (self.get_uri(),
                                self.rangestart,
                                self.rangeend)

    def tree_decode(self, tree_nodenames):
        " Given a list of nodes leading to this, returns the node. "
        node_uri = self.get_uri() + Tree.DELIMITER + \
                   Tree.DELIMITER.join(tree_nodenames)
        
        return Tree.get_by_uri(node_uri)

    def tree_create(self, tree_nodenames):
        " Given a list of nodes leading to this, returns the node, will create if doesn't exist. "
        node_uri = self.get_uri() + Tree.DELIMITER + \
                   Tree.DELIMITER.join(tree_nodenames)

        return Tree.get_by_uri(node_uri, create = True)

    def tree_encode(self):
        " Returns a list of nodes leading from root to this node. "
        return self.get_uri().split(Tree.DELIMITER)

    def get_uri(self):
        " Returns the uniform resource identifier "
        if self.uri_correct:
            return self.uri

        if self.id == Tree.ROOT_ID:
            self.uri_correct = True
            self.uri = ''
            self.save(uri_fix = True)
            return ''
        
        parent_uri = self.parent.get_uri()
        if parent_uri == '':
            self.uri = self.name
        else:
            self.uri = parent_uri + Tree.DELIMITER + self.name
            
        self.uri_correct = True

        if self.id is not None:
            self.save(uri_fix = True)

        return self.uri
        
    def descendants(self):
        " All nodes below this node. "
        return Tree.objects.filter(rangestart__gte = self.rangestart,
                                   rangeend__lte   = self.rangeend)

    def ancestors(self):
        " All nodes above this node. "
        return Tree.objects.filter(rangestart__lte = self.rangestart,
                                   rangeend__gte   = self.rangeend)
    
    def children(self):
        " Return all the subnodes of this one. "
        return Tree.objects.filter(parent = self)

    def range_size(self):
        " The capacity of this node. "
        return self.rangeend - self.rangestart - 1

    def room_for_children(self):
        return self.range_size() - self.children().count() 
    

    ####################################
    # DICTIONARY-like BEHAVIOR         #
    ####################################
    def __len__(self):
        return self.children().count()

    values = children

    def keys(self):
        return [node.name for node in self.children()]

    def items(self):
        return [(node.name, node) for node in self.children()]

    def has_key(self, key):
        return self.children().filter(name__exact = key).count() > 0

    def __contains__(self, child):
        if type(child) != Tree:
            return False
        return self.descendants().filter(id = child.id).count() > 0
    

    def __getitem__(self, key):
        try:
            return Tree.objects.get(parent = self, name = key)
        except:
            raise exceptions.KeyError, key


    def __setitem__(self, key, value):
        if type(value) != Tree:
            assert False, "Expected a Tree"
        try:
            other_child = Tree.objects.get(parent = self,
                                           name   = key)
            other_child.friendly_name = value.friendly_name
            other_child.save()
            return other_child
        except:
            value.name   = key
            value.parent = self
            value.save()


    #############################
    # STATIC ACCESSORS          #
    #############################
    @staticmethod
    def root():
        " Get the root node of this tree. "
        try:
            return Tree.objects.get(id = Tree.ROOT_ID)
        except:
            root = Tree( name = 'ROOT', id = Tree.ROOT_ID)
            root.save(True)
            return root
    
    @staticmethod
    def get_by_uri(uri, create = False):
        " Get the node by the URI, A/B/.../asdf "
        # first we strip
        uri = uri.strip(Tree.DELIMITER)
        try:
            node = Tree.objects.get(uri = uri,
                                    uri_correct = True)
            return node
        except:
            pass
        
        if uri == '':
            return Tree.root()

        pieces = uri.split(Tree.DELIMITER)
        cur_name   = pieces[-1]
        parent_uri = Tree.DELIMITER.join(pieces[:-1])
        parent = Tree.get_by_uri(parent_uri, create)
        
        try:
            node = parent[cur_name]
            return node
        except:
            pass

        if not create:
            return None
        
        parent[cur_name] = Tree(uri = uri)
        node = parent[cur_name]
        node.uri_correct = True
        node.save(uri_fix = True)
        return node


    ##############################
    # SQL Helpers                #
    ##############################
    @transaction.commit_manually
    def expire_uri(self):
        " Expire the URIs on all descendants of this node. "
        from django.db import connection
        from django.conf import settings

        false = settings.DATABASE_ENGINE == 'mysql' and '0' or 'f'
        cursor = connection.cursor()

        cursor.execute(("UPDATE %s SET uri_correct = %s WHERE " + \
                        "rangestart > %s AND rangeend <= %s") % \
                       (Tree._meta.db_table, false,
                        self.rangestart, self.rangeend))

        transaction.commit()

    @transaction.commit_manually
    def delete_descendants(self):
        " Delete all the descendants of this node from the database. "
        from django.db import connection
        cursor = connection.cursor()

        cursor.execute(("DELETE FROM %s WHERE rangestart > %s AND " \
                        "rangeend <= %s") % (Tree._meta.db_table,
                                             self.rangestart,
                                             self.rangeend))
        transaction.commit()

    @staticmethod
    @transaction.commit_manually
    def shift_many_ranges(baserange, amount, above_base = True):
        " Shift all ranges either above or below a base by amount. "
        from django.db import connection

        if amount == 0:
            return
        cursor = connection.cursor()

        stramount = ''
        if amount > 0:
            stramount = '+ %s' % amount
        else:
            stramount = '- %s' % abs(amount)

        op = (above_base and '>=' or '<=')
        
        cursor.execute(("UPDATE %s SET rangestart = rangestart %s " +\
                       "WHERE rangestart %s %s") % (Tree._meta.db_table,
                                                  stramount,op,baserange))
        cursor.execute(("UPDATE %s SET rangeend = rangeend %s " +\
                       "WHERE rangeend %s %s") % (Tree._meta.db_table,
                                                stramount,op,baserange))
        transaction.commit()

        
    @staticmethod
    @transaction.commit_manually
    def shift_all_ranges(amount):
        " Shift all ranges by an amount, either positive or negative. "
        from django.db import connection

        if amount == 0:
            return
        
        cursor = connection.cursor()
        
        stramount = ''
        if amount > 0:
            stramount = '+ %s' % amount
        else:
            stramount = '- %s' % abs(amount)
            
            cursor.execute("UPDATE Tree SET rangeend = rangeend %s, " +\
                           "rangestart = rangestart %s" % [stramount,stramount])
        
        transaction.commit()
        

    ##################
    # EXCEPTIONS     #
    ##################
    class CannotCreateRootException(Exception):
        pass

    class PermissionDenied(Exception):
        pass




####################
# HELPER FUNCTIONS #
####################

def GetNode(nodename):
    " Get a datatree node and create it if it doesn't exist. "
    return Tree.get_by_uri(nodename, create = True)

