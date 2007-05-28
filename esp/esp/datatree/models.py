"""
The DataTree organizes the ESP site into a heirarchal structure that
can do some pretty interesting things pretty fast.
"""
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
from django.db.models import Q
from django.db import transaction
from esp.db.fields import AjaxForeignKey
import exceptions


class DataTree(models.Model):
    " This model organizes the site into a tight heirarchy. "
    FIXING_TREE = False

    # choices for LOCK state
    lock_choices = (
        (0, "UNLOCKED"),
        (1, "SOFT LOCK"),
        (2, "HARD LOCK"),
        )

    # Parameters for the tree
    START_SIZE  = 2
    DELIMITER   = '/'
    ROOT_NODE   = None
    ROOT_NAME   = 'ROOT'
    MAX_DEPTH   = 50
    LOCK_WAIT   = .01
    MAX_WAIT    = 15  # Maximum time to wait for a tree unlock
    PERCENT_BAD = .10 # percent of nodes that have to be bad
                      # before a "rebuild" without "reinsert"
                      

    # some fields
    name          = models.CharField(maxlength=64)
    friendly_name = models.TextField()
    parent        = AjaxForeignKey('self',blank=True,null=True, related_name='child_set')
    rangestart    = models.IntegerField(editable = False)
    rangeend      = models.IntegerField(editable = False)
    uri           = models.CharField(editable = False, maxlength=1024)
    #^ a charfield for indexing purposes
    uri_correct   = models.BooleanField(editable = False, default = False)
    lock_table    = models.IntegerField(editable = False, default = 0,
                                        choices  = lock_choices)
    range_correct = models.BooleanField(editable = False, default = True )

    class Meta:
        # parent and name should be unique
        unique_together = (("name", "parent"),)
        # ordering should be by rangestart
        ordering = ['rangestart','-rangeend']

    class Admin:
        search_fields = ['uri']
        pass

    ########################
    # PARAMETER Functions  #
    ########################

    @staticmethod
    def expanded_size(node):
        " This is whatever the expanded size should be. "
        size = node.range_size()
        if size < 2:
            return 2
        else:
            return 2*size

    @staticmethod
    def expand_conservative(node):
        " This will expand conservatively. "
        size = node.range_size()
        return size + DataTree.START_SIZE

    #######################
    # MUTATORS            #
    #######################
    @transaction.commit_on_success
    def delete(self, recurse = False, superdelete = False):
        " Delete tree nodes. "
        
        if superdelete:
            return super(DataTree, self).delete()


        DataTree.fix_tree_if_broken()

        # we are going to wait if the tree is locked
        DataTree.wait_if_locked()


        # need these for later
        rangestart = self.rangestart
        rangeend   = self.rangeend

        if len(self) > 0:
            if not recurse:
                raise DataTree.PermissionDenied, "You cannot delete a tree without deleting its children."
            
            self.delete_descendants(commit_wait = True)

        # move all of the tree nodes to the left.
        DataTree.shift_many_ranges(rangestart,
                               rangestart - rangeend - 1,
                               commit_wait = True)

        return super(DataTree, self).delete()
        

    @transaction.commit_on_success
    def save(self, create_root = False, uri_fix = False, old_save = False, start_size = None):
        " This will save the tree, using the rules of a tree. "
        if start_size is None: start_size = DataTree.START_SIZE

        new_node = False

        
        if self.name.find(DataTree.DELIMITER) != -1:
            raise DataTree.InvalidName, "You cannot use '%s' in the name field." % DataTree.DELIMITER

        if old_save:
            return super(DataTree, self).save()


        DataTree.fix_tree_if_broken()
            

        # we are going to wait if the tree is locked
        DataTree.wait_if_locked()

        if self.id is not None:
            node = DataTree.objects.filter(id = self.id)
            if node.count() > 0 and not create_root:
                if not uri_fix:
                    self.expire_uri()

                # we're going to silently revert
                # any changes to the ranges,
                # since editable = False doesn't do anything
                node = node[0]
                self.rangestart = node.rangestart
                self.rangeend   = node.rangeend
                new_node = super(DataTree, self).save()
                transaction.commit()
                if node.parent_id != self.parent_id:
                    self.reinsert()
                    
                return new_node
        
#        if not create_root and self.parent is None:
#            raise DataTree.CannotCreateRootException, "You cannot create a root node."
        # if the parent is something
        if self.parent_id is not None:
            # get the ranges for a new child
            self.rangestart, self.rangeend = self.parent.new_ranges(start_size)
        else:
            self.rangestart = 0
            self.rangeend   = start_size - 1
            # make room for this tree node
            DataTree.shift_all_ranges(start_size, commit_wait = True)
        
        new_node =  super(DataTree, self).save()
        return new_node
    

    def expand(self, expand_func = None):
        " Make this parent now have room."

        if expand_func is None: expand_func = DataTree.expanded_size
        
        DataTree.shift_many_ranges(self.rangeend,
                                   expand_func(self),
                                   commit_wait = True)


    def rcopy(self, destination, child = False):
        " Recursively copies from this node to the destination node. "
        if child:
            try:
                newnode = DataTree.objects.get(parent = destination,
                                           name   = self.name)
            except:
                newnode = DataTree()
                newnode.__dict__.update(self.__dict__)
                newnode.id          = None
                newnode.uri_correct = False
                newnode.parent      = destination
                
            newnode.save(start_size = self.range_size())
            #print '%s --> %s' % (self, newnode)
            destination = newnode

        for child in self.children():
            child.rcopy(destination, True)
        return True

    def rebuild_range(self, rangestart = 0):
        " This will rebuild the range for everything below this. "

        self.rangestart = rangestart

        rangeend = rangestart

        if self.children().count() == 0:
            rangeend = rangestart + 1
        else:
            for child in self.children().order_by('name'):
                rangeend = child.rebuild_range(rangeend+1)

        
        self.rangeend = rangeend
        
        self.save(old_save = True)
        return rangeend+1

    def reinsert(self, top = True):
        " Will perform a Re-insert. That is, it will rotate this to the last node. "

        if top:
            DataTree.wait_if_locked()
            DataTree.lock()

        children = self.children().order_by('name')
        size     = len(self.descendants_slow())

        if self.parent_id is None:
            self.rangestart, self.rangeend = (0, DataTree.START_SIZE*size+1)
        else:
            self.rangestart, self.rangeend = self.parent.new_ranges((size-1)*DataTree.START_SIZE+\
                                                                    DataTree.START_SIZE-1,
                                                                    DataTree.expand_conservative)


        try:
            transaction.commit()
        except:
            pass
        
        self.range_correct = True
        self.save(old_save = True)

        for child in self.children():
            child.range_correct = False
            child.save(old_save = True)

        for child in self.children():
            child.reinsert(top = False)
        
        if top: DataTree.unlock()

    


    ######################
    # ACCESSORS          #
    ######################

    @classmethod
    def ajax_autocomplete(cls, data):

        data_pieces = data.strip().split(cls.DELIMITER)
        if len(data_pieces) == 1:
            parent = DataTree.root()
        else:
            try:
                parent = cls.get_by_uri(cls.DELIMITER.join(data_pieces[:-1]))
            except:
                return []

        tail = data_pieces[-1]
        
        query_set = parent.children()

        if tail.strip() != '':
            query_set = query_set.filter(name__istartswith = tail)

        values = query_set.order_by('rangestart').values('uri', 'id')

        for value in values:
            value['ajax_str'] = value['uri']
        return values

    def ajax_str(self):
        return self.uri

    def is_root(self):
        """ If this node is the root node, returns True, otherwise False."""
        return self.parent_id == None and self.name == DataTree.ROOT_NAME
        
    
    def __str__(self):
        return '%s (%s--%s)' % (self.get_uri(),
                                self.rangestart,
                                self.rangeend)

    def tree_decode(self, tree_nodenames):
        " Given a list of nodes leading to this, returns the node. "
        node_uri = self.get_uri() + DataTree.DELIMITER + \
                   DataTree.DELIMITER.join(tree_nodenames)
        
        return DataTree.get_by_uri(node_uri)

    def tree_create(self, tree_nodenames):
        " Given a list of nodes leading to this, returns the node, will create if doesn't exist. "
        node_uri = self.get_uri() + DataTree.DELIMITER + \
                   DataTree.DELIMITER.join(tree_nodenames)

        return DataTree.get_by_uri(node_uri, create = True)


    def new_ranges(self, start_size = None, expand_func = None):
        " Returns a 2-tuple (min,max) of range values for a new child under this one. "
        if start_size is None: start_size = DataTree.START_SIZE

        children = self.children().filter(range_correct = True).order_by('-rangeend')
        if children.count() > 0:           
            upperbound = children[0].rangeend
        else:
            upperbound = self.rangestart

        if upperbound < self.rangestart:
            upperbound = self.rangestart
        
        if self.rangeend < (upperbound + start_size + 2):
            # we dont' have enough room...time to expand
            self.expand(expand_func)
                
        return upperbound+1, upperbound + start_size

    def tree_encode(self):
        " Returns a list of nodes leading from root to this node. "
        return self.get_uri().split(DataTree.DELIMITER)

    def get_uri(self):
        " Returns the uniform resource identifier "
        if self.uri_correct:
            return self.uri

        if self.is_root():
            self.uri_correct = True
            self.uri = ''
            self.save(uri_fix = True)
            return ''
        
        parent_uri = self.parent.get_uri()
        if parent_uri == '':
            self.uri = self.name
        else:
            self.uri = parent_uri + DataTree.DELIMITER + self.name
            
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
        
    def descendants(self, distinct = True):
        " All nodes below this node. "
        desc = DataTree.objects.filter(rangestart__gte = self.rangestart,
                                   rangeend__lte   = self.rangeend)

        if distinct:
            desc = desc.distinct()
        return desc

    def ancestors(self, distinct = True):
        " All nodes above this node. "
        anc = DataTree.objects.filter(rangestart__lte = self.rangestart,
                                      rangeend__gte   = self.rangeend)
        if distinct:
            anc = anc.distinct()
        return anc
    
    def children(self):
        " Return all the subnodes of this one. "
        return DataTree.objects.filter(parent = self)

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
        if type(child) != DataTree:
            return False
        return self.descendants().filter(id = child.id).count() > 0
    

    def __getitem__(self, key):
        try:
            return DataTree.objects.get(parent = self, name = key)
        except:
            raise exceptions.KeyError, key


    def __setitem__(self, key, value):
        if type(value) != DataTree:
            assert False, "Expected a DataTree"
        try:
            if self.id is None:
                self.save()
                
            other_child = DataTree.objects.get(parent = self,
                                           name   = key)
            other_child.friendly_name = value.friendly_name
            other_child.save()
            return other_child
        except:
            value.name   = key
            value.parent = self
            value.save()


    ###########################
    # STATIC LOCKs            #
    ###########################

    @staticmethod
    def lock(hard_lock = False):
        " Lock the entire tree. "
        root = DataTree.root()
        
        lock = 1
        if hard_lock: lock = 2
        
        root.lock_table = lock
        
        root.save(old_save = True)

    @staticmethod
    def unlock():
        " Unlock the entire tree. "
        root = DataTree.root()
        root.lock_table = 0
        root.save(old_save = True)

    #############################
    # STATIC ACCESSORS          #
    #############################


    @classmethod
    def root(cls):
        " Get the root node of this tree. "
        
        try:
            cls.ROOT_NODE = cls.objects.get(name = cls.ROOT_NAME,
                                            parent__isnull = True)
            return cls.ROOT_NODE
        except cls.DoesNotExist:
            root = cls( name = cls.ROOT_NAME,
                        uri  = '/',
                        uri_correct = True,
                        rangestart = 0,
                        rangeend = 0+cls.START_SIZE - 1)
            root.save(True, old_save = True)

            return root

    @staticmethod
    def locked():
        " Get the lock status of this tree. "
        return DataTree.root().lock_table

    @staticmethod
    def wait_if_locked():
        " Will wait if there is a lock on the root node. "
        import time, datetime
        old = datetime.datetime.now()
        while DataTree.root().lock_table != 0:
            time.sleep(DataTree.LOCK_WAIT)
            if (datetime.datetime.now() - old).seconds > DataTree.MAX_WAIT:
                raise DataTree.LockTimedOut, 'A lock was on the tree for more than %s seconds.' %\
                      DataTree.MAX_WAIT
        return
    
    @staticmethod
    def get_by_uri(uri, create = False):
        " Get the node by the URI, A/B/.../asdf "
        # first we strip
        
        uri = uri.strip(DataTree.DELIMITER)
        
        try:
            node = DataTree.objects.get(uri = uri,
                                    uri_correct = True)
            return node
        except:
            pass
        
        if uri == '':
            return DataTree.root()

        pieces = uri.split(DataTree.DELIMITER)
        if len(pieces) > DataTree.MAX_DEPTH:
            raise DataTree.MaxDepthExceeded, "You cannot go more than %s levels deep." % DataTree.MAX_DEPTH
        
        cur_name   = pieces[-1]
        parent_uri = DataTree.DELIMITER.join(pieces[:-1])
        parent = DataTree.get_by_uri(parent_uri, create)
        
        try:
            node = parent[cur_name]
            return node
        except:
            pass

        if not create:
            raise DataTree.NoSuchNodeException(parent, uri)
        
        parent[cur_name] = DataTree(uri = uri)
        node = parent[cur_name]
        node.uri_correct = True
        node.save(uri_fix = True)
        return node

    @staticmethod
    def violating_dup_rangestart(QObject = False):
        " Returns the list of nodes violating the rangestart-must-be-unique constraint. "
        return DataTree.find_unused_and_dup_ranges(QObject)[1]

    @staticmethod
    def find_unused_and_dup_ranges(QObject = False, lock = True):
        " This will return a tuple of (list, violating nodes) for using a range multiple times. "
        violating_nodes = []
        if lock: DataTree.lock()
        
        nodes = DataTree.objects.all()

        rangemax = nodes.order_by('-rangeend')[0].rangeend

        nodes  = list(nodes.values('id','rangestart'))

        try:
            ranges = [False for x in range(rangemax)]
        except:
            return ([],[])

        for i in range(len(nodes)):
            node = nodes[i]
            if ranges[node['rangestart']]:
                violating_nodes.append(node['id'])
            else:
                ranges[node['rangestart']] = True

        if len(violating_nodes) == 0:
            Q_violating = Q(id = -10000)
        else:
            Q_violating = Q(id__in = violating_nodes)

        unused_range = [num for num in range(len(ranges)) if ranges[num] is False]
        unused_ranges = []
        
        cur_ranges = [unused_range[0],unused_range[0]]
        last_range = unused_range[0]
        
        for num in unused_range[1:]:
            if num == last_range + 1:
                cur_ranges = (cur_ranges[0], num)
            else:
                unused_ranges.append(cur_ranges)
                cur_ranges = (num, num)
            last_range = num

        

        if lock: DataTree.unlock()

        if QObject:
            return (unused_ranges, Q_violating)
        else:
            return (unused_ranges, DataTree.objects.filter(Q_violating))

        
        


    ###########################
    # STATIC FILTERS          #
    ###########################

    @staticmethod
    def get_only_parents(queryset, slow = False):
        """
        Given an arbitrary list of nodes, removes the nodes that are `under'
        another node in the list. Returns a queryset for homogeneity.
        """

        # NB: I avoid using ranges for the consistency of the tree.
        ids = []
        uris = {}
        for node in queryset:
            uris[node.id] = node.get_uri()

        for node in queryset:
            cur_uri = node.get_uri()
            found = False
            for uri in [uri for uri in uris.values()
                        if len(uri) < len(cur_uri)   ]:
                if node.get_uri().find(uri) == 0:
                    try:
                        del uris[node.id]
                    except:
                        pass
                    found = True

            if not found:
                ids.append(node.id)

        return DataTree.objects.filter(id__in = ids)

        

    ############################
    # STATIC FIXERS            #
    ############################

    @staticmethod
    def rebuild_tree_ranges(top = True):
        " This will rebuild the tree ranges. "

        DataTree.wait_if_locked()
        DataTree.lock(hard_lock = True)
        
        DataTree.root().rebuild_range()
        
        DataTree.unlock()
        


    @staticmethod
    def fix_tree_if_broken():
        " This will fix all the broken nodes in the table. "

        if DataTree.FIXING_TREE:
            return
        
        DataTree.FIXING_TREE = True

        res = DataTree.all_violators()
        num_bad = res.count()
        if num_bad == 0:
            DataTree.FIXING_TREE = False
            return False

        total = DataTree.objects.count()
        
        if float(num_bad) / float(total) < DataTree.PERCENT_BAD:
            # if the tree is "insertable"
            for parent in DataTree.get_only_parents(res):
                parent.reinsert()

            if DataTree.all_violators().count() == 0:
                DataTree.FIXING_TREE = False
                return True

        DataTree.rebuild_tree_ranges()
        
        DataTree.FIXING_TREE = False
        return True


    @staticmethod
    def zip_ranges():
        " This will compactify all the ranges into a neat, little enclosure. "
        DataTree.lock()
        
        ranges = DataTree.find_unused_and_dup_ranges(QObject = True, lock = False)[0]
        ranges.reverse()

        for ran in ranges:
            DataTree.shift_many_ranges(ran[0], ran[0] - ran[1]-1, above_base = True, commit_wait = True)
            
        transaction.commit()
        DataTree.unlock()
        

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


    def delete_descendants(self, commit_wait = False):
        " Delete all the descendants of this node from the database. "
        from django.db import connection

        cursor = connection.cursor()

        table = DataTree._meta.db_table

        cursor.execute("DELETE FROM %s WHERE rangestart > %s AND rangeend <= %s" % \
                       (table, self.rangestart, self.rangeend,))


        if not commit_wait:
            transaction.commit()


    @staticmethod
    def all_violators():
        " Returns all nodes in violation of the constraints. "
        import operator
        # these are a list of functions which return violators
        violate_list = [DataTree.violating_range_sign_nodes,
                        DataTree.violating_range_nodes      ]
        
        Q_final = reduce(operator.or_, [func(QObject = True) for func in violate_list])
        
        return DataTree.objects.filter(Q_final).distinct()

    @staticmethod
    def violating_range_sign_nodes(QObject = False):
        " Returns the nodes that violate the rangestart-must-be-less-than-rangeend constaint. "
        from django.db import connection

        cursor = connection.cursor()

        table = DataTree._meta.db_table

        cursor.execute("SELECT id FROM %s WHERE rangestart >= rangeend" % table)

        ids = [id[0] for id in cursor.fetchall()]

        if len(ids) == 0:
            Q_violating = Q(id = -10000)
        else:
            Q_violating = Q(id__in = ids)

        if QObject:
            return Q_violating
        
        return DataTree.objects.filter(Q_violating)


    @staticmethod
    def violating_range_nodes(QObject = False):
        " Returns the nodes that violate the must-be-in-range-of-parent constraint "

        from django.db import connection
        
        cursor = connection.cursor()

        table = DataTree._meta.db_table

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
            
        if QObject:
            return Q_violating
        
        return DataTree.objects.filter(Q_violating)
    
    def expire_uri(self, commit_wait = False):
        " Expire the URIs on all descendants of this node. "
        from django.db import connection
        from django.conf import settings

        if self.rangestart is None or self.rangeend is None:
            return


        if 'postgresql' in settings.DATABASE_ENGINE.lower():
            false = 'f'
        elif 'mysql' in settings.DATABASE_ENGINE.lower():
            false = '0'
        elif 'sqlite' in settings.DATABASE_ENGINE.lower():
            false = 'False'
        else:
            false = '0'
            
        cursor = connection.cursor()

        cursor.execute(("UPDATE %s SET uri_correct = '%s' WHERE " + \
                        "rangestart > %s AND rangeend <= %s") % \
                       (DataTree._meta.db_table, false,
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


        if 'postgres' in settings.DATABASE_ENGINE.lower() or \
           'mysql'    in settings.DATABASE_ENGINE.lower():
            template = 'postgresql' in settings.DATABASE_ENGINE.lower() and \
                       "CASE WHEN %s %s %s THEN %s %s ELSE %s END" or \
                       "IF(%s %s %s, %s %s, %s)"                         

            rangestart_result = template % \
                                ('rangestart', op, baserange, 'rangestart', stramount, 'rangestart')
        
            rangeend_result   = template %\
                                ('rangeend', op, baserange, 'rangeend', stramount, 'rangeend')

        
            sql = ("UPDATE %s SET rangestart = %s, " +\
                   "rangeend = %s WHERE "            +\
                   "rangestart %s %s OR rangeend %s %s") % \
                        (DataTree._meta.db_table,
                         rangestart_result,
                         rangeend_result,
                         op,baserange,
                         op,baserange)
            
            
        elif 'sqlite' in settings.DATABASE_ENGINE.lower():
            sql = ['UPDATE %s SET rangestart = rangestart %s WHERE rangestart %s %s;' % \
                    (DataTree._meta.db_table,
                    stramount, op, baserange),
                   'UPDATE %s SET rangeend   = rangeend   %s WHERE rangeend   %s %s;' % \
                   (DataTree._meta.db_table,
                    stramount, op, baserange)]
        else:
            assert False, 'Unkown database engine %s.' % settings.DATABASE_ENGINE

        if isinstance(sql, basestring):
            sql = [sql]

        for strsql in sql:
            cursor.execute(strsql)
            
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
            
        cursor.execute("UPDATE DataTree SET rangeend = rangeend %s, " +\
                       "rangestart = rangestart %s" % [stramount,stramount])
        
        if not commit_wait:
            transaction.commit()

    ##################
    # EXCEPTIONS     #
    ##################
    class CannotCreateRootException(Exception):
        pass

    class LockTimedOut (Exception):
        pass

    class MaxDepthExceeded(Exception):
        pass
    
    class InvalidName(Exception):
        pass
    class PermissionDenied(Exception):
        pass

    class NoSuchNodeException(Exception):
        """ Raised if a required node in a DataTree doesn't exist """
        def __init__(self, anchor, remainder):
            self.anchor = anchor
            self.remainder = remainder

        def __str__(self):
            return "Node not found: " + repr(self.remainder[0])

                                                        

    ###########################
    # BACKWARDS Compatibility #
    ###########################
    antecedents = ancestors

    full_name   = get_uri
    


    ##############
    # TESTS      #
    ##############
    @staticmethod
    def randwordtest(factor = 4):
        # some random test
        import sys
        import random
        try:
            f = open('/usr/share/dict/words')
            words = [word.strip() for word in f ]

            try:
                low_id = DataTree.objects.order_by('id')[1].id
            except:
                low_id = 1

                
            while True:
                try:
                    size = int(DataTree.objects.count())
                    cur_id = random.choice(range(low_id,low_id + size*factor))
                    print 'Tried %s' % cur_id
                    nodes = DataTree.objects.filter(id = cur_id)
                    if nodes.count() > 0:
                        node = nodes[0]
                        node.delete(True)
                        print 'Deleted %s' % node
                    else:
                        node = DataTree.get_by_uri('/'.join(random.choice(words)), True)
                        print 'Added %s' % node
                    
                    if DataTree.violating_range_sign_nodes().count() > 0:
                        print "ERROR:"
                        print DataTree.violating_range_sign_nodes()
                        return
                except:
                    exc_info = sys.exc_info()
                    print exc_info[0], exc_info[1], exc_info[2]

        except:
            exc_info = sys.exc_info()
            raise exc_info[0], exc_info[1], exc_info[2]


####################
# HELPER FUNCTIONS #
####################


def get_lowest_parent(uri):
    " Returns the lowest parent of a given URI. "
    try:
        node = DataTree.get_by_uri(uri)
    except:
        node = None
        
    while node is None:
        uri  = DataTree.DELIMITER.join(uri.split(DataTree.DELIMITER)[:-1])
        try:
            node = DataTree.get_by_uri(uri)
        except:
            node = None

    return node

def GetNode(nodename):
    " Get a datatree node and create it if it doesn't exist. "
    return DataTree.get_by_uri(nodename, create = True)

def StringToPerm(permstr):
    """ Convert a permission from 'a/b/c' format to [a, b, c] format """
    return permstr.split('/')

def PermToString(perm):
    """ Convert a permission from [a, b, c] format to 'a/b/c' format """
    if perm == []:
        return ''
    else:
        return "/".join(perm)

#root = DataTree.root()
#root.save()



