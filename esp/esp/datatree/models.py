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
Copyright (c) 2008 MIT ESP

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
import time

from django.conf import settings

from django.db import models
from django.db.models import Q
from django.db import connection
from django.db import transaction
from django.core.cache import cache
from esp.db.fields import AjaxForeignKey
from esp.utils.memdb import mem_db
from esp.datatree.sql.query_utils import *
from esp.datatree.sql.manager import DataTreeManager


__all__ = ('DataTree', 'GetNode', 'QTree', 'get_lowest_parent', 'StringToPerm', 'PermToString')

qn = connection.ops.quote_name

import exceptions


class DataTree(models.Model):
    " This model organizes the site into a tight heirarchy. "
    FIXING_TREE = False
    SAFE_COLS = ('name', 'friendly_name', 'parent_id', 'uri', 'uri_correct', 'lock_table')
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
    LOCK_WAIT   = .1
    MAX_WAIT    = 6000  # Maximum time to wait for a tree unlock
    PERCENT_BAD = .10 # percent of nodes that have to be bad
                      # before a "rebuild" without "reinsert"


    # some fields
    name          = models.CharField(max_length=64)
    friendly_name = models.TextField()
    parent        = AjaxForeignKey('self',blank=True,null=True, related_name='child_set')
    rangestart    = models.IntegerField(editable = False)
    rangeend      = models.IntegerField(editable = False)
    uri           = models.CharField(editable = False, max_length=1024)
    #^ a charfield for indexing purposes
    uri_correct   = models.BooleanField(editable = False, default = False)
    lock_table    = models.IntegerField(editable = False, default = 0,
                                        choices  = lock_choices)
    range_correct = models.BooleanField(editable = False, default = True )

    objects = DataTreeManager()

    class Meta:
        # parent and name should be unique
        unique_together = (("name", "parent"),)
        # ordering should be by rangestart
        #ordering = ['rangestart','-rangeend']

    class Admin:
        ordering = ('rangestart', '-rangeend')

    ## functions returning rangestart and rangeend, that Adam will edit at some point. -rye
    def get_rangestart(self):
        return self.rangestart

    def get_rangeend(self):
        return self.rangeend

    #######################
    # MUTATORS            #
    #######################
    def delete(self, recurse = False, superdelete = False):
        " Delete tree nodes. "
        if superdelete:
            return super(DataTree, self).delete()

        DataTree.objects.fix_tree_if_broken()

        # we are going to wait if the tree is locked
        DataTree.wait_if_locked()

        # need these for later
        rangestart = self.get_rangestart()
        rangeend   = self.get_rangeend()

        if len(self) > 0:
            if not recurse:
                raise DataTree.PermissionDenied("You cannot delete a tree without deleting its children.")

            self.delete_descendants()

        # move all of the tree nodes to the left.
        DataTree.objects._change_ranges(self)

        return super(DataTree, self).delete()


    def save(self, create_root=False, uri_fix=False, old_save=False, start_size=None, *args, **kwargs):
        " This will save the tree, using the rules of a tree. "
        if old_save:
            return models.Model.save(self, *args, **kwargs)

        if not self.id:
            obj = DataTree.objects.create(name=self.name, friendly_name=self.name, parent=self.parent, start_size=start_size, uri=self.uri)
            self.__dict__.update(obj.__dict__)
            return self

        old_node = DataTree.objects.get(id=self.id)
        if old_node.parent_id != self.parent_id:
            raise NotImplementedError("Have not yet written the parent moving code.")

        self.save_db(*self.SAFE_COLS)


    def save_db(self, *cols, **kwargs):
        # Update the db with this item, but only for the columns listed.
        cursor = kwargs.pop('cursor', None)
        if not self.id:
            raise AttributeError("The node's id is required!")
        sql_cols = []
        params = []
        for col in cols:
            sql_cols.append(qn(col))
            params.append(getattr(self, col))
        params.append(self.id)
        sql = "UPDATE %s SET %s WHERE id = %%s" % (
            qn(self._meta.db_table),
            ", ".join("%s = %%s" % col for col in sql_cols)
            )
        if not cursor:
            cursor = connection.cursor()
        cursor.execute(sql, params)


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

    def move_ranges_to_parent(self):
        " Shift all the ranges under and including this node to another parent. "
        range = DataTree.objects.get(id = self.id).values('rangestart', 'rangeend')
        range = range['rangeend'] - range['rangestart'] + 1
        self.rangestart, self.rangeend = DataTree.objects.new_ranges(parent, range)
        self.save(old_save=True)

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
            self.rangestart, self.rangeend = DataTree.objects.new_ranges(self.parent,
                                                                         (size - 1) * DataTree.START_SIZE)
        self.range_correct = True
        self.save(old_save = True)

        for child in self.children():
            child.range_correct = False
            child.save(old_save = True)

        for child in self.children():
            child.reinsert(top = False)

        transaction.commit()

        if top:
            DataTree.unlock()




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
        return self.parent_id is None and self.name == DataTree.ROOT_NAME

    def __unicode__(self):
        return '%s (%s--%s)' % (self.get_uri(),
                                self.get_rangestart(),
                                self.get_rangeend())

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

    def tree_encode(self):
        " Returns a list of nodes leading from root to this node. "
        return self.get_uri().split(DataTree.DELIMITER)

    def get_uri(self, save=True):
        " Returns the uniform resource identifier "
        if self.uri_correct:
            return self.uri

        if self.is_root():
            self.uri_correct = True
            self.uri = ''
            if save:
                self.save(uri_fix=True)
            return ''

        parent_uri = self.parent.get_uri()
        if parent_uri == '':
            self.uri = self.name
        else:
            self.uri = parent_uri + DataTree.DELIMITER + self.name

        self.uri_correct = True

        if self.id is not None and save:
            self.save(uri_fix = True)

        return self.uri

    def descendants_slow(self, memo=None):
        " All nodes below this node, but very slowly. "
        if memo is None:
            import sys
            sys.stderr.write("ENTERED descendants_slow!\n")
            memo = set()
        children = self.children()
        if not children[:1]:
            return [self]
        memo.add(self)

        children_list = []

        for child in children:
            if child not in memo:
                children_list += child.descendants_slow()

        return children_list

    def descendants(self, distinct = True):
        " All nodes below this node. "
        desc = DataTree.objects.filter(QTree(below = self))

        if distinct:
            desc = desc.distinct()
        return desc

    def ancestors(self, distinct = True):
        " All nodes above this node. "
        anc = DataTree.objects.filter(QTree(above = self))
        if distinct:
            anc = anc.distinct()
        return anc

    def sync_ranges(self):
        node = DataTree.objects.get(id = self.id)
        self.rangestart, self.rangeend = node.rangestart, node.rangeend
        cache.set("GetNode%s" % self.get_uri(), self, 86400)

    def children(self, only_if_known = False):
        " Return all the subnodes of this one. "

        if hasattr(self, "_children"):
            return self._children
        elif not only_if_known:
            children = DataTree.objects.filter(parent = self)
            setattr(self, "_children", children)
            return self._children
        else:
            return None

    def depth(self):
        uri = self.get_uri()
        if uri == '':
            return 0
        else:
            return len(self.get_uri().split('/'))

    # function that returns a boolean if self is a descendant of node.
    def is_descendant_of(self, node):
        return bool(DataTree.objects.filter(QTree(below = node), id = self.id)[:1])

    # same, but if self is an ancestor of node.
    def is_ancestor_of(self, node):
        return bool(DataTree.objects.filter(QTree(above = node), id = self.id)[:1])

    ####################################
    # DICTIONARY-like BEHAVIOR         #
    ####################################
    def __len__(self):
        return self.children().count()

    def __nonzero__(self):
        """
        Django occasionally uses bool(model_object) internally, to determine whether an object was properly returned (if not, presumably model_object is null or something).
        bool(a) calls __nonzero__ on a; if that doesn't exist, it calls __len__.
        DataTree().__len__ (above) calls DataTree().children(), which executes a query, which calls DataTree().__len__..., creating an infinite loop.
        So, creating this function to stop that.
        """
        return True

    values = children

    def keys(self):
        return [node.name for node in self.children()]

    def items(self):
        return [(node.name, node) for node in self.children()]

    def has_key(self, key):
        # If we already know the children of this node,
        # don't bother querying for them;
        # just scan the list for this particular child
        children = self.children()
        if children != None:
            return key in (child.name for child in children)
        else:
            return bool(self.children().filter(name__exact = key)[:1])

    def __contains__(self, child):
        if type(child) != DataTree:
            return False
        return bool(self.descendants().filter(id = child.id)[:1])


    def __getitem__(self, key):
        # If we already know the children of this node,
        # don't bother querying for them;
        # just scan the list for this particular child
        children = self.children(only_if_known=True)
        if children != None:
            for child in children:
                if child.name == key:
                    return child
            # Key must not be in the set of children
            raise exceptions.KeyError, key
        else:
            try:
                return DataTree.objects.get(parent = self, name = key)
            except:
                raise exceptions.KeyError, key


    def __setitem__(self, key, value):
        assert isinstance(value, DataTree), "Expected a DataTree"
        value.name = key
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

        mem_db.set('datatree_lock', str(lock))

        root.lock_table = lock

        root.save(old_save = True)

    @staticmethod
    def unlock():
        " Unlock the entire tree. "
        root = DataTree.root()
        root.lock_table = 0

        mem_db.set('datatree_lock', '0')

        root.save(old_save = True)

    #############################
    # STATIC ACCESSORS          #
    #############################


    @classmethod
    def root(cls):
        " Get the root node of this tree. "
        if cls.ROOT_NODE != None:
            return cls.ROOT_NODE

        try:
            cls.ROOT_NODE = cls.objects.get(name = cls.ROOT_NAME,
                                            parent__isnull = True)
            return cls.ROOT_NODE
        except cls.DoesNotExist:
            root = cls( name = cls.ROOT_NAME,
                        uri  = '',
                        uri_correct = True,
                        rangestart = 0,
                        rangeend = 0+cls.START_SIZE * 10)
            root.save(True, old_save = True)
            return root

    @staticmethod
    def locked():
        " Get the lock status of this tree. "
        try:
            lock_table = int(mem_db.get('datatree_lock'))
        except (TypeError, ValueError):
            lock_table = DataTree.root().lock_table
            mem_db.set('datatree_lock', lock_table)

        return lock_table

    @staticmethod
    def wait_if_locked():
        " Will wait if there is a lock on the root node. "
        import time, datetime
        old = datetime.datetime.now()
        while DataTree.locked() != 0:
            time.sleep(DataTree.LOCK_WAIT)
            if (datetime.datetime.now() - old).seconds > DataTree.MAX_WAIT:
                raise DataTree.LockTimedOut, 'A lock was on the tree for more than %s seconds.' %\
                      DataTree.MAX_WAIT
        return

    @staticmethod
    def get_by_uri(uri, create=False):
        return DataTree.objects.get(uri=uri, create=create)


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
        DataTree.objects.filter(QTree(belowonly = self)).delete()


    @staticmethod
    def violating_range_nodes(QObject = False):
        " Returns the nodes that violate the must-be-in-range-of-parent constraint "

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

    @transaction.commit_manually
    def expire_uri(self, commit_wait = False):
        " Expire the URIs on all descendants of this node. "

        if self.get_rangestart() is None or self.get_rangeend() is None:
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
        db_tree = qn(DataTree._meta.db_table)

        cursor.execute(("UPDATE %s SET uri_correct = '%s' WHERE " + \
                        "rangestart > (SELECT rangestart FROM %s WHERE id = %s)" + \
                        " AND rangeend <= (SELECT rangeend FROM %s WHERE id = %s)") % \
                           (db_tree, false, db_tree, self.id, db_tree, self.id))

        if not commit_wait:
            try:
                transaction.commit()
            except transaction.TransactionManagementError:
                pass # We're not actually in a transaction; so don't bother

    @classmethod
    def shift_many_ranges(cls, baserange, amount, above_base = True, commit_wait = False):
        " Shift all ranges either above or below a base by amount. "
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
                        (cls._meta.db_table,
                         rangestart_result,
                         rangeend_result,
                         op,baserange,
                         op,baserange)


        elif 'sqlite' in settings.DATABASE_ENGINE.lower():
            sql = ['UPDATE %s SET rangestart = rangestart %s WHERE rangestart %s %s;' % \
                    (cls._meta.db_table,
                    stramount, op, baserange),
                   'UPDATE %s SET rangeend   = rangeend   %s WHERE rangeend   %s %s;' % \
                   (cls._meta.db_table,
                    stramount, op, baserange)]
        else:
            assert False, 'Unkown database engine %s.' % settings.DATABASE_ENGINE

        if isinstance(sql, basestring):
            sql = [sql]

        for strsql in sql:
            cursor.execute(strsql)

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

        def __unicode__(self):
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
    def randwordtest(factor = 4, limit = -1):
        # some random test
        import sys
        import random
        error_free = True
        GetNode('a')
        try:
            f = open('/usr/share/dict/words')
            words = [word.strip().decode('cp1250', 'replace') for word in f ]

            try:
                low_id = DataTree.objects.order_by('id')[1].id
            except int:
                low_id = 1


            while limit != 0:
                if limit > 0:
                    limit -= 1
                try:
                    size = int(DataTree.objects.count())
                    cur_id = random.choice(range(low_id,low_id + size*factor))
                    #print 'Tried %s' % cur_id
                    nodes = DataTree.objects.filter(id = cur_id)
                    if nodes[:1]:
                        node = nodes[0]
                        print u'Deleting %s' % node
                        node.delete(True)
                        print u'Deleted %s' % node
                    else:
                        uri = '/'.join(random.choice(words))
                        node = DataTree.get_by_uri(uri, True)
                        print u'Added %s' % uri

                    if DataTree.objects.exists_violators():
                        print "ERROR:"
                        print DataTree.objects.exists_violators(queryset=True)
                        return False
                except int:
                    exc_info = sys.exc_info()
                    print exc_info[0], exc_info[1], exc_info[2]
                    error_free = False

        except int:
            exc_info = sys.exc_info()
            raise exc_info[0], exc_info[1], exc_info[2]

        return error_free


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


def install():
    """
    This function sets up the initial ROOT, Q, and V nodes in the datatree.
    It's idempotent; ie., you can run it multiple times without harm.
    """
    root_node = DataTree.root()
    root_node.get_by_uri('Q', create=True)
    root_node.get_by_uri('V', create=True)

    from esp.datatree.tree_template import genTemplate
    genTemplate()
