
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
""" This is the views portion of the users utility, which has some user-oriented views."""
from esp.middleware   import ESPError
from django.db.models.query    import Q
from esp.users.models import DBList, PersistentQueryFilter, ESPUser, User, ZipCode
from esp.web.util     import render_to_response
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

    if type(listDict2) != dict or len(listDict2) == 0:
        raise ESPError(), 'User lists were not specified correctly!'

    listDict = {}

    for key, value in listDict2.items():
        listDict[key] = {'list': getQForUser(value['list']),
                         'description': value['description']}


    if request.POST.has_key('select_mailman'):
        from esp.mailman import list_members
        import operator

        lists = request.POST.getlist('select_mailman')

        all_list_members = reduce(operator.or_, (list_members(x) for x in lists))
        filterObj = PersistentQueryFilter.getFilterFromQ(Q(id__in=[x.id for x in all_list_members]), User, 'Custom Mailman filter: ' + ", ".join(lists))

        if request.POST['submitform'] == 'I want to search within this list':
            getUser, found = search_for_user(request, User.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, True)
            if found:
                if type(getUser) == User or type(getUser) == ESPUser:
                    newfilterObj = PersistentQueryFilter.getFilterFromQ(Q(id = getUser.id), User, 'User %s' % getUser.username)
                else:
                    newfilterObj = PersistentQueryFilter.getFilterFromQ(filterObj.get_Q() & getUser, User, 'Custom user filter')
                return (newfilterObj, True)
            else:
                return (getUser, False)

        elif request.POST['submitform'] == 'I want a subset of this list':
            getUsers, found = get_user_checklist(request, User.objects.filter(filterObj.get_Q()).distinct(), filterObj.id)
            if found:
                newfilterObj = PersistentQueryFilter.getFilterFromQ(getUsers, User, 'Custom list')
                return (newfilterObj, True)
            else:
                return (getUsers, False)

        return (filterObj, True) # We got the list, return it.
        

    if request.POST.has_key('submit_checklist') and \
            request.POST['submit_checklist'] == 'true':

        # If we're coming back after having checked off users from a checklist...
        filterObj = PersistentQueryFilter.getFilterFromID(request.POST['extra'], User)
        getUsers, found = get_user_checklist(request, User.objects.filter(filterObj.get_Q()).distinct(), filterObj.id)
        if found:
            # want to make a PersistentQueryFilter out of this returned query
            newfilterObj = PersistentQueryFilter.getFilterFromQ(getUsers, User, 'Custom list')
            return (newfilterObj, True)
        else:
            return (getUsers, False)
    

    if request.POST.has_key('submit_user_list') and \
       request.POST['submit_user_list'] == 'true':

        # If a user list was submitted....
        import operator

        # map of operators that can be done on lists (appropriately, Q Objects)
        opmapping = {'and'  : operator.and_,
                     'or'   : operator.or_,
                     'not'  : (lambda x: ~x), # aseering 7/12/2008 -- Should work with Django SVN HEAD
                     'ident': (lambda x: x) # for completeness
                     }

        # this is the "first" list...the list we start with.
        if listDict.has_key(request.POST['base_list']):
            curList = listDict[request.POST['base_list']]['list']
        else:
            raise ESPError(), 'I do not know of list "%s".' % request.POST['base_list']
        
        # we start with all the sparated lists, and apply the and'd lists onto the or'd lists before
        # we or. This closely represents the sentence (it's not as powerful, but makes "sense")
        separated = {'or': [curList], 'and': []}


        # use double-commas because it's safer?
        keys = request.POST['keys'].split(',,')

        for key in keys:
            if request.POST.has_key('operator_'+key) and \
               request.POST['operator_'+key]         and \
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


        filterObj = PersistentQueryFilter.getFilterFromQ(curList, User, request.POST['finalsent'])


        if request.POST['submitform'] == 'I want to search within this list':
            getUser, found = search_for_user(request, User.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, True)
            if found:
                if type(getUser) == User or type(getUser) == ESPUser:
                    newfilterObj = PersistentQueryFilter.getFilterFromQ(Q(id = getUser.id), User, 'User %s' % getUser.username)
                else:
                    newfilterObj = PersistentQueryFilter.getFilterFromQ(filterObj.get_Q() & getUser, User, 'Custom user filter')
                return (newfilterObj, True)
            else:
                return (getUser, False)

        elif request.POST['submitform'] == 'I want a subset of this list':
            getUsers, found = get_user_checklist(request, User.objects.filter(filterObj.get_Q()).distinct(), filterObj.id)
            if found:
                newfilterObj = PersistentQueryFilter.getFilterFromQ(getUsers, User, 'Custom list')
                return (newfilterObj, True)
            else:
                return (getUsers, False)

        return (filterObj, True) # We got the list, return it.


    # if we found a single user:
    if request.method == 'GET' and request.GET.has_key('op') and request.GET['op'] == 'usersearch':
        filterObj = PersistentQueryFilter.getFilterFromID(request.GET['extra'], User)
        getUser, found = search_for_user(request, User.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, True)
        if found:
            if type(getUser) == User or type(getUser) == ESPUser:
                newfilterObj = PersistentQueryFilter.getFilterFromQ(Q(id = getUser.id), User, 'User %s' % getUser.username)
            else:
                newfilterObj = PersistentQueryFilter.getFilterFromQ(filterObj.get_Q() & getUser, User, 'Custom user filter')         

            if 'usersearch_containers' in request.session:
                request.POST, request.GET = request.session['usersearch_containers']
                del request.session['usersearch_containers']   

            return (newfilterObj, True)
        
        else:
            return (getUser, False)


    if request.GET.has_key('advanced'):
        # we're going to prepare a list to send out.
        arrLists = []

        pickled_post = pickle.dumps(request.POST)
        pickled_get  = pickle.dumps(request.GET)

        request.session['usersearch_containers'] = (pickled_post, pickled_get)
        
        for key, value in listDict.items():
            arrLists.append(DBList(key = key, QObject = value['list'], description = value['description'].strip('.'))) # prepare a nice list thing.
        
        arrLists.sort(reverse=True) 

        return (render_to_response('users/create_list.html', request, None, {'lists': arrLists}), False) # No, we didn't find it yet...
    else:
        from esp.mailman import all_lists
        public_lists = all_lists()
        nonpublic_lists = list( set(all_lists(show_nonpublic=True)) - set(public_lists) )
        return (render_to_response('users/select_mailman_list.html', request, None, {'public_lists': public_lists, 'nonpublic_lists': nonpublic_lists}), False) # No, we didn't find it yet...

def get_user_checklist(request, userList, extra=''):
    """ Generate a checklist of users given an initial list of users to pick from.
        Returns a tuple (userid_query or response, users found?)
        The query that's returned contains the id's of just the users which are checked off. """

    if request.POST.has_key('submit_checklist') and \
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

    return (render_to_response('users/userchecklist.html', request, None, context), False) # make the checklist


def search_for_user(request, user_type='Any', extra='', returnList = False):
	""" Interface to search for a user. If you need a user, just use this.
	  Returns (user or response, user returned?) """

	users = None
	error = False
	QSUsers = None


	# Get the "base list" consisting of all the users of a specific type, or all the users.
	if type(user_type) != str:
		All_Users = user_type
	elif user_type == 'Any':
		All_Users = ESPUser.objects.all()
	else:
		if user_type not in ESPUser.getTypes():
                    raise ESPUser(), 'user_type must be one of '+str(ESPUser.getTypes())

		All_Users = ESPUser.getAllOfType(user_type, False)

        Q_include = Q()
        Q_exclude = Q()
        
        Q_exclude.old = True
        Q_include.old = True
        
        update   = False


	if (request.GET.has_key('userid') and len(request.GET['userid'].strip()) > 0) or (request.POST.has_key('userid') and len(request.POST['userid'].strip()) > 0):

            
            userid = -1

            try:
                if request.GET.has_key('userid'):
                    userid_str = request.GET['userid']
                if request.POST.has_key('userid'):
                    userid_str = request.POST['userid']

                userid = userid_str.split(',')
    
            except:
                raise ESPError(False), 'User id invalid, please enter a number or comma-separated list of numbers.'

            if request.GET.has_key('userid__not'):
                Q_exclude &= Q(id__in = userid)
            else:
                Q_include &= Q(id__in = userid)
            update = True

        else:
            for field in ['username','last_name','first_name', 'email']:
                if request.GET.has_key(field) and len(request.GET[field].strip()) > 0:
                    filter_dict = {'%s__iregex' % field: request.GET[field]}
                    update = True
                    if request.GET.has_key('%s__not' % field):
                        Q_exclude &= Q(**filter_dict)
                    else:
                        Q_include &= Q(**filter_dict)

            if request.GET.has_key('zipcode') and request.GET.has_key('zipdistance') and \
               len(request.GET['zipcode'].strip()) > 0 and len(request.GET['zipdistance'].strip()) > 0:
                try:
                    zipc = ZipCode.objects.get(zip_code = request.GET['zipcode'])
                except:
                    raise ESPError(False), 'Please enter a valid US zipcode.'
                zipcodes = zipc.close_zipcodes(request.GET['zipdistance'])
                # Excludes zipcodes within a certain radius, giving an annulus; can fail to exclude people who used to live outside the radius.
                # This may have something to do with the Q_include line below taking more than just the most recent profile. -ageng, 2008-01-15
                if request.GET.has_key('zipdistance_exclude') and len(request.GET['zipdistance_exclude'].strip()) > 0:
                    zipcodes_exclude = zipc.close_zipcodes(request.GET['zipdistance_exclude'])
                    zipcodes = [ zipcode for zipcode in zipcodes if zipcode not in zipcodes_exclude ]
                if len(zipcodes) > 0:
                    Q_include &= Q(registrationprofile__contact_user__address_zip__in = zipcodes)
                    update = True

            if request.GET.has_key('states') and len(request.GET['states'].strip()) > 0:
                state_codes = request.GET['states'].strip().upper().split(',')
                if request.GET.has_key('states__not'):
                    Q_exclude &= Q(registrationprofile__contact_user__address_state__in = state_codes)
                else:
                    Q_include &= Q(registrationprofile__contact_user__address_state__in = state_codes)
                update = True

            if request.GET.has_key('grade_min'):
                yog = ESPUser.YOGFromGrade(request.GET['grade_min'])
                if yog != 0:
                    update = True
                    Q_include &= Q(registrationprofile__student_info__graduation_year__lte = yog)

            if request.GET.has_key('grade_max'):
                yog = ESPUser.YOGFromGrade(request.GET['grade_max'])
                if yog != 0:
                    update = True                    
                    Q_include &= Q(registrationprofile__student_info__graduation_year__gte = yog)
        
        if not update:
            users = None
	else:

            QSUsers = All_Users

            if not hasattr(Q_include,'old') or Q_include.old is False:
                QSUsers = QSUsers.filter(Q_include)
            if not hasattr(Q_exclude,'old') or Q_exclude.old is False:
                QSUsers = QSUsers.exclude(Q_exclude)
            QSUsers = QSUsers.distinct()

            
            users = [ ESPUser(user) for user in QSUsers ]

	if users is not None and len(users) == 0:
		error = True
                users = None
        
        if users is None:
            return (render_to_response('users/usersearch.html', request, None, {'error': error, 'extra':extra,  'list': returnList}), False)
        if len(users) == 1:
            return (users[0], True)
        else:

            users.sort()

            if (request.GET.has_key('listokay') and request.GET['listokay'] == 'true') or \
               (request.GET.has_key('submitform') and request.GET['submitform'] == 'Use Filtered List'):
                Q_Filter = None
                if not hasattr(Q_include, 'old'):
                    Q_Filter = Q_include
                    if not hasattr(Q_exclude, 'old'):
                        Q_Filter &= ~Q_exclude
                else:
                    if not hasattr(Q_exclude, 'old'):
                        Q_Filter = ~Q_exclude
                

                return (Q_Filter, True)
            
            context = {'users': users, 'extra':str(extra), 'list': returnList}

            return (render_to_response('users/userpick.html', request, None, context), False)


def getQForUser(QRestriction):
    # Let's not do anything and say we did...
    #return QRestriction
    
    from esp.users.models import User
    ids = [ x['id'] for x in User.objects.filter(QRestriction).values('id')]
    if len(ids) == 0:
        return Q(id = -1)
    else:
        return Q(id__in = ids)

