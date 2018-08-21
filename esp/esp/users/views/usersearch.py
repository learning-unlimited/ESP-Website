
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""
""" This is the views portion of the users utility, which has some user-oriented views."""

import logging
logger = logging.getLogger(__name__)

from esp.middleware   import ESPError
from django.db.models.query    import Q
from esp.users.models import DBList, PersistentQueryFilter, ESPUser, User
from esp.utils.web import render_to_response
from esp.users.controllers.usersearch import UserSearchController
from django.db.models.query import QuerySet
from django.conf import settings
import pickle

def get_user_list(request, listDict2, extra=''):
    """ Get a list of users from some complicated mixture of other lists.
        The listDict must be of the form:
          {'list1_key': {'list:         Q_Object,
                         'description': "UseFul_Description"}
            ...
          }

        This will return a tuple (userlist_or_response, found_list).
        If found_list is True, then userlist_or_response is a UserList object.

        Otherwise, it returns a response that's expected to be returned to django.
        """

    if (not isinstance(listDict2, dict)) or len(listDict2) == 0:
        raise ESPError('User lists were not specified correctly!')

    listDict = {}

    for key, value in listDict2.items():
        listDict[key] = {'list': getQForUser(value['list']),
                         'description': value['description']}


    if 'select_mailman' in request.POST:
        from esp.mailman import list_members
        import operator

        lists = request.POST.getlist('select_mailman')

        all_list_members = reduce(operator.or_, (list_members(x) for x in lists))
        filterObj = PersistentQueryFilter.getFilterFromQ(Q(id__in=[x.id for x in all_list_members]), ESPUser, 'Custom Mailman filter: ' + ", ".join(lists))

        if request.POST['submitform'] == 'I want to search within this list':
            getUser, found = search_for_user(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, True)
            if found:
                if isinstance(getUser, User):
                    newfilterObj = PersistentQueryFilter.getFilterFromQ(Q(id = getUser.id), ESPUser, 'User %s' % getUser.username)
                else:
                    newfilterObj = PersistentQueryFilter.getFilterFromQ(filterObj.get_Q() & getUser, ESPUser, 'Custom user filter')
                return (newfilterObj, True)
            else:
                return (getUser, False)

        elif request.POST['submitform'] == 'I want a subset of this list':
            getUsers, found = get_user_checklist(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id)
            if found:
                newfilterObj = PersistentQueryFilter.getFilterFromQ(getUsers, ESPUser, 'Custom list')
                return (newfilterObj, True)
            else:
                return (getUsers, False)

        return (filterObj, True) # We got the list, return it.


    if request.POST.get('submit_checklist') == 'true':
        # If we're coming back after having checked off users from a checklist...
        filterObj = PersistentQueryFilter.getFilterFromID(request.POST['extra'], ESPUser)
        getUsers, found = get_user_checklist(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id)
        if found:
            # want to make a PersistentQueryFilter out of this returned query
            newfilterObj = PersistentQueryFilter.getFilterFromQ(getUsers, ESPUser, 'Custom list')
            return (newfilterObj, True)
        else:
            return (getUsers, False)


    if request.POST.get('submit_user_list') == 'true':
        # If a user list was submitted....
        import operator

        # map of operators that can be done on lists (appropriately, Q Objects)
        opmapping = {'and'  : operator.and_,
                     'or'   : operator.or_,
                     'not'  : (lambda x: ~x), # aseering 7/12/2008 -- Should work with Django SVN HEAD
                     'ident': (lambda x: x) # for completeness
                     }

        # this is the "first" list...the list we start with.
        if request.POST['base_list'] in listDict:
            curList = listDict[request.POST['base_list']]['list']
        else:
            raise ESPError('I do not know of list "%s".' % request.POST['base_list'])

        # we start with all the sparated lists, and apply the and'd lists onto the or'd lists before
        # we or. This closely represents the sentence (it's not as powerful, but makes "sense")
        separated = {'or': [curList], 'and': []}


        # use double-commas because it's safer?
        keys = request.POST['keys'].split(',,')

        for key in keys:
            if request.POST.get('operator_'+key) and \
               request.POST['operator_'+key] != 'ignore':     # and it's not ignore (it should be 'and' or 'or')
                # We are adding to the list of 'and'd' lists and 'or'd' lists.
                separated[request.POST['operator_'+key]].append(opmapping[request.POST['not_'+key]](listDict[key]['list']))


        # ^ - now separated has all the necessary Q objects.

        # essentially the below turns: a OR b AND c OR d ... into: (a AND c) or (b AND c) or (d AND c)

        # now we can apply the ands on all the or'd lists separately
        for i in range(len(separated['or'])):
            for j in range(len(separated['and'])):
                separated['or'][i] = opmapping['and'](separated['or'][i], separated['and'][j])

        # and now we OR the leftover ors
        curList = separated['or'][0]
        for List in separated['or'][1:]:
            curList = opmapping['or'](curList, List)


        filterObj = PersistentQueryFilter.getFilterFromQ(curList, ESPUser, request.POST['finalsent'])


        if request.POST['submitform'] == 'I want to search within this list':
            getUser, found = search_for_user(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, True)
            if found:
                if isinstance(getUser, User):
                    newfilterObj = PersistentQueryFilter.getFilterFromQ(Q(id = getUser.id), ESPUser, 'User %s' % getUser.username)
                else:
                    newfilterObj = PersistentQueryFilter.getFilterFromQ(filterObj.get_Q() & getUser, ESPUser, 'Custom user filter')
                return (newfilterObj, True)
            else:
                return (getUser, False)

        elif request.POST['submitform'] == 'I want a subset of this list':
            getUsers, found = get_user_checklist(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id)
            if found:
                newfilterObj = PersistentQueryFilter.getFilterFromQ(getUsers, ESPUser, 'Custom list')
                return (newfilterObj, True)
            else:
                return (getUsers, False)

        return (filterObj, True) # We got the list, return it.


    # if we found a single user:
    if request.method == 'GET' and request.GET.get('op') == 'usersearch':
        filterObj = PersistentQueryFilter.getFilterFromID(request.GET['extra'], ESPUser)
        getUser, found = search_for_user(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, True)
        if found:
            if isinstance(getUser, ESPUser):
                newfilterObj = PersistentQueryFilter.getFilterFromQ(Q(id = getUser.id), ESPUser, 'User %s' % getUser.username)
            else:
                newfilterObj = PersistentQueryFilter.getFilterFromQ(filterObj.get_Q() & getUser, ESPUser, 'Custom user filter')

            if 'usersearch_containers' in request.session:
                request.POST, request.GET = request.session['usersearch_containers']
                del request.session['usersearch_containers']

            return (newfilterObj, True)

        else:
            return (getUser, False)


    if 'advanced' in request.GET or not settings.USE_MAILMAN:
        # we're going to prepare a list to send out.
        arrLists = []

        pickled_post = pickle.dumps(request.POST)
        pickled_get  = pickle.dumps(request.GET)

        request.session['usersearch_containers'] = (pickled_post, pickled_get)

        for key, value in listDict.items():
            arrLists.append(DBList(key = key, QObject = value['list'], description = value['description'].strip('.'))) # prepare a nice list thing.

        arrLists.sort(reverse=True)

        return (render_to_response('users/create_list.html', request, {'lists': arrLists}), False) # No, we didn't find it yet...
    else:
        from esp.mailman import all_lists
        public_lists = all_lists()
        nonpublic_lists = list( set(all_lists(show_nonpublic=True)) - set(public_lists) )
        return (render_to_response('users/select_mailman_list.html', request, {'public_lists': public_lists, 'nonpublic_lists': nonpublic_lists}), False) # No, we didn't find it yet...

def get_user_checklist(request, userList, extra='', nextpage=None):
    """ Generate a checklist of users given an initial list of users to pick from.
        Returns a tuple (userid_query or response, users found?)
        The query that's returned contains the id's of just the users which are checked off. """

    if 'submit_checklist' in request.POST and \
       request.POST['submit_checklist'] == 'true':
        UsersQ = Q(id=-1)

        for key in request.POST.keys():
            if 'userno' in key:
                try:
                    val = int(request.POST[key])
                    UsersQ |= Q(id=val)
                except:
                    pass

        return (UsersQ, True)

    context = {}
    context['extra'] = extra
    context['users'] = userList
    if nextpage is None:
        context['nextpage'] = request.path
    else:
        context['nextpage'] = nextpage

    return (render_to_response('users/userchecklist.html', request, context), False) # make the checklist


def search_for_user(request, user_type='Any', extra='', returnList = False, add_to_context = None):
    """ Interface to search for a user. If you need a user, just use this.
        Returns (user or response, user returned?) """

    users = None
    error = False

    usc = UserSearchController()
    if isinstance(user_type, basestring):
        user_query = usc.query_from_criteria(user_type, request.GET)
        QSUsers = ESPUser.objects.filter(user_query).distinct()
    elif isinstance(user_type, QuerySet):
        QSUsers = usc.filter_from_criteria(user_type, request.GET)
    else:
        raise ESPError('Invalid user_type: %s' % type(user_type), log=True)

    #   We need to ask for more user input if no filtering options were selected
    if not usc.updated:
        users = None
    else:
        users = [ user for user in QSUsers ]

    if users is not None and len(users) == 0:
        error = True
        users = None

    if users is None:
        context = {'error': error, 'extra':extra,  'list': returnList}
        if add_to_context:
            context.update(add_to_context)
        return (render_to_response('users/usersearch.html', request, context), False)

    if len(users) == 1:
        return (users[0], True)

    else:

        users.sort()

        if request.GET.get('listokay') == 'true' or \
           request.GET.get('submitform') == 'Use Filtered List':
            Q_Filter = Q(id__in=QSUsers.values_list('id', flat=True))
            return (Q_Filter, True)

        context = {'users': users, 'extra':str(extra), 'list': returnList}
        if add_to_context:
            context.update(add_to_context)

        return (render_to_response('users/userpick.html', request, context), False)

def getQForUser(QRestriction):
    # Let's not do anything and say we did...
    #return QRestriction

    from esp.users.models import ESPUser
    ids = [ x['id'] for x in ESPUser.objects.filter(QRestriction).values('id')]
    if len(ids) == 0:
        return Q(id = -1)
    else:
        return Q(id__in = ids)

