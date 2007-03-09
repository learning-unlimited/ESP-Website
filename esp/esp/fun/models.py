from django.db import models
from django.db.models import Q
from django.db import transaction
import exceptions

class Tree(models.Model):
    " This model organizes the site into a tight heirarchy. "

    START_SIZE  = 2
    DELIMITER   = '/'
    ROOT_ID     = 1
    MAX_DEPTH   = 50

    name        = models.CharField(maxlength=64)
    parent      = models.ForeignKey('self',blank=True,null=True)
    rangestart  = models.IntegerField(editable = False)
    rangeend    = models.IntegerField(editable = False)
    uri         = models.CharField(editable = False, maxlength=1024)
    #^ a charfield for indexing purposes
    uri_correct = models.BooleanField(editable = False, default = False)
    lock_table  = models.BooleanField(editable = False, default = False)

    class Meta:
        # parent and name should be unique
        unique_together = (("name", "parent"),)
        # ordering should be by rangestart
        ordering = ['rangestart']

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
    @transaction.commit_on_success
    def delete(self, recurse = False, superdelete = False):
        " Delete tree nodes. "
        if superdelete:
            return super(Tree, self).delete()

        # need these for later
        rangestart = self.rangestart
        rangeend   = self.rangeend

        if len(self) > 0:
            if not recurse:
                raise Tree.PermissionDenied, "You cannot delete a tree without deleting its children."
            
            self.delete_descendants()

        # move all of the tree nodes to the left.
        Tree.shift_many_ranges(rangestart,
                               rangestart - rangeend - 1,
                               commit_wait = True)

        return super(Tree, self).delete()
        

    @transaction.commit_on_success
    def save(self, create_root = False, uri_fix = False, old_save = False):
        # fall back to g'old save
        new_node = False
        
        if self.name.find(Tree.DELIMITER) != -1:
            raise Tree.InvalidName, "You cannot use '%s' in the name field." % Tree.DELIMITER

        if old_save:
            return super(Tree, self).save()

        if self.id is not None:
            node = Tree.objects.filter(id = self.id)
            if node.count() > 0 and not create_root:
                if not uri_fix:
                    self.expire_uri()

                # we're going to silently revert
                # any changes to the ranges,
                # since editable = False doesn't do anything
                node = node[0]
                self.rangestart = node.rangestart
                self.rangeend   = node.rangeend
                
                new_node = super(Tree, self).save()
                transaction.commit()
                return new_node
        
        if not create_root and self.parent is None:
            raise Tree.CannotCreateRootException, "You cannot create a root node."
        # if the parent is something
        if self.parent_id is not None:
            # get the ranges for a new child
            self.rangestart, self.rangeend = self.parent.new_ranges()
        else:
            self.rangestart = 0
            self.rangeend   = Tree.START_SIZE - 1
            # make room for this tree node
            Tree.shift_all_ranges(Tree.START_SIZE, commit_wait = True)
            
        new_node =  super(Tree, self).save()
        return new_node
    

    def expand(self):
        " Make this parent now have room."
        Tree.shift_many_ranges(self.rangeend,
                               self.expanded_size(), commit_wait = True)


    def delete_descendants(self):
        " Delete all the descendants of this node from the database. "
        self.descendants().exclude(id = self.id).delete()
            

    def reinsert(self):
        " Will perform a Re-insert. That is, it will rotate this to the last node. "
        pass
        # if the parent is something
        #if self.parent_id is not None:
        #    # get the ranges for a new child
        #    self.rangestart, self.rangeend = self.parent.new_ranges()
        


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

    def new_ranges(self):
        " Returns a 2-tuple (min,max) of range values for a new child under this one. "
        siblings = self.children().order_by('-rangeend')
        if siblings.count() > 0:
            upperbound = siblings[0].rangeend
        else:
            upperbound = self.rangestart

        if self.rangeend < (upperbound + Tree.START_SIZE):
            # we dont' have enough room...time to expand
            self.expand()
                
        return upperbound + 1, upperbound + Tree.START_SIZE

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

    def descendants_slow(self):
        " All nodes below this node, but very slowly. "
        children = self.children()
        if len(self) == 0:
            return [self]
        children_list = [self]

        for child in children:
            children_list += child.descendants_slow()

        return children_list
        
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
    
    def depth(self):
        uri = self.get_uri()
        if uri == '':
            return 0
        else:
            return len(self.get_uri().split('/'))

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
    def wait_if_locked():
        " Will wait if there is a lock on the root node. "
        import time
        time.sleep()
        
    
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
        if len(pieces) > Tree.MAX_DEPTH:
            raise Tree.MaxDepthExceeded, "You cannot go more than %s levels deep." % Tree.MAX_DEPTH
        
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

    ############################
    # STATIC FIXERS            #
    ############################

    @staticmethod
    def fix_ranges():
        " This will fix all the broken nodes in the table. "
        
        violating_children = Tree.violating_nodes()
        if violating_children.count() == 0:
            return False

        violating_children = list(violating_children)
        violating_children.sort(Tree.sort_by_depth_rangestart)

        #for node in violating_children:
            

    #############################
    # SORTERS                   #
    #############################

    @staticmethod
    def sort_by_depth_rangestart(one, two):
        " This will sort nodes by their depth and their range start descendingly. "
        cmp1 = cmp(two.depth(), one.depth())
        if cmp1 != 0:
            return cmp1

        cmp1 = cmp(two.rangestart, one,rangestart)
        return cmp1

    ##############################
    # SQL Helpers                #
    ##############################

    @staticmethod
    def violating_range_sign_nodes():
        " Returns the nodes that violate the rangestart-must-be-less-than-rangeend constaint. "
        from django.db import connection

        cursor = connection.cursor()

        table = Tree._meta.db_table

        cursor.execute("SELECT id FROM %s WHERE rangestart >= rangeend" % table)

        ids = [id[0] for id in cursor.fetchall()]

        if len(ids) == 0:
            Q_violating = Q(id = -10000)
        else:
            Q_violating = Q(id__in = ids)

        return Tree.objects.filter(Q_violating)


    @staticmethod
    def violating_range_nodes():
        " Returns the nodes that violate the must-be-in-range-of-parent constraint "

        from django.db import connection
        
        cursor = connection.cursor()

        table = Tree._meta.db_table

        cursor.execute(("SELECT %s.id FROM %s INNER JOIN %s AS parent_tree " + \
                        "ON %s.parent_id = parent_tree.id "                  + \
                        "WHERE %s.rangestart <= parent_tree.rangestart OR "  + \
                        "%s.rangeend > parent_tree.rangeend") % \
                       (table, table, table, table, table, table))

        ids = [id[0] for id in cursor.fetchall()]

        if len(ids) == 0:
            Q_violating = Q(id = -10000)
        else:
            Q_violating = Q(id__in = ids)

        return Tree.objects.filter(Q_violating)
    
    def expire_uri(self, commit_wait = False):
        " Expire the URIs on all descendants of this node. "
        from django.db import connection
        from django.conf import settings

        if self.rangestart is None or self.rangeend is None:
            return

        false = settings.DATABASE_ENGINE == 'mysql' and '0' or 'f'
        cursor = connection.cursor()

        cursor.execute(("UPDATE %s SET uri_correct = '%s' WHERE " + \
                        "rangestart > %s AND rangeend <= %s") % \
                       (Tree._meta.db_table, false,
                        self.rangestart, self.rangeend))

        if not commit_wait:
            transaction.commit()

            
    @staticmethod
    def shift_many_ranges(baserange, amount, above_base = True, commit_wait = False):
        " Shift all ranges either above or below a base by amount. "
        from django.db import connection
        from django.conf import settings
        
        if amount == 0:
            return
        cursor = connection.cursor()

        stramount = ''
        if amount > 0:
            stramount = '+ %s' % amount
        else:
            stramount = '- %s' % abs(amount)

        op = (above_base and '>=' or '<=')


        template = settings.DATABASE_ENGINE == 'postgresql' and \
                   "CASE WHEN %s %s %s THEN %s %s ELSE %s END" or \
                   "IF(%s %s %s, %s %s, %s)"                         

        rangestart_result = template % ('rangestart', op, baserange, 'rangestart', stramount, 'rangestart')
        rangeend_result = template % ('rangeend', op, baserange, 'rangeend', stramount, 'rangeend')

        
                                        
        # this MUST stay as one query, even though it could be two for sanity's sake
        cursor.execute(("UPDATE %s SET rangestart = %s, " +\
                        "rangeend = %s WHERE "            +\
                        "rangestart %s %s OR rangeend %s %s") %
                       (Tree._meta.db_table,
                        rangestart_result,
                        rangeend_result,
                        op,baserange,
                        op,baserange))
    
        if not commit_wait:
            transaction.commit()
        
    @staticmethod
    def shift_all_ranges(amount, commit_wait = False):
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
        
        if not commit_wait:
            transaction.commit()

    ##################
    # EXCEPTIONS     #
    ##################
    class CannotCreateRootException(Exception):
        pass

    class MaxDepthExceeded(Exception):
        pass
    
    class InvalidName(Exception):
        pass
    class PermissionDenied(Exception):
        pass


    ##############
    # TESTS      #
    ##############
    @staticmethod
    def randwordtest(factor = 4):
        # some random test
        import random
        try:
            f = open('/usr/share/dict/words')
            words = [word.strip() for word in f ]

            try:
                low_id = Tree.objects.order_by('id')[1].id
            except:
                low_id = 1

                
            while True:
                size = int(Tree.objects.count())
                cur_id = random.choice(range(low_id,low_id + size*factor))
                print 'Tried %s' % cur_id
                nodes = Tree.objects.filter(id = cur_id)
                if nodes.count() > 0:
                    node = nodes[0]
                    node.delete(True)
                    print 'Deleted %s' % node
                else:
                    node = Tree.get_by_uri('/'.join(random.choice(words)), True)
                    print 'Added %s' % node

                if Tree.violating_range_sign_nodes().count() > 0:
                    print "ERROR:"
                    print Tree.violating_range_sign_nodes()
                    return
        except:
            pass

####################
# HELPER FUNCTIONS #
####################

def GetNode(nodename):
    " Get a datatree node and create it if it doesn't exist. "
    return Tree.get_by_uri(nodename, create = True)

