""" This is the views portion of the users utility, which has some user-oriented views."""
from esp.middleware   import ESPError
from django.db.models.query import Q, QNot
from esp.users.models import DBList, PersistentQueryFilter, ESPUser, User
from esp.web.util     import render_to_response

def get_user_list(request, listDict, extra=''):
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

    if type(listDict) != dict or len(listDict) == 0:
        raise ESPError(), 'User lists were not specified correctly!'

    if request.POST.has_key('submit_user_list') and \
       request.POST['submit_user_list'] == 'true':

        # If a user list was submitted....
        import operator

        # map of operators that can be done on lists (appropriately, Q Objects)
        opmapping = {'and'  : operator.and_,
                     'or'   : operator.or_,
                     'not'  : QNot,
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
            getUser, found = search_for_user(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, True)
            if found:
                if type(getUser) == User or type(getUser) == ESPUser:
                    newfilterObj = PersistentQueryFilter.getFilterFromQ(Q(id = getUser.id), User, 'User %s' % getUser.username)
                else:
                    newfilterObj = PersistentQueryFilter.getFilterFromQ(filterObj.get_Q() & getUser, User, 'Custom user filter')
                return (newfilterObj, True)
            else:
                return (getUser, False)

        return (filterObj, True) # We got the list, return it.

    # if we found a single user:
    if request.method == 'GET' and request.GET.has_key('op') and request.GET['op'] == 'usersearch':
        filterObj = PersistentQueryFilter.getFilterFromID(request.GET['extra'], User)
        getUser, found = search_for_user(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, True)
        if found:
            if type(getUser) == User or type(getUser) == ESPUser:
                newfilterObj = PersistentQueryFilter.getFilterFromQ(Q(id = getUser.id), User, 'User %s' % getUser.username)
            else:
                newfilterObj = PersistentQueryFilter.getFilterFromQ(filterObj.get_Q() & getUser, User, 'Custom user filter')                

                
            return (newfilterObj, True)
        else:
            return (getUser, False)

    # we're going to prepare a list to send out.
    arrLists = []

    for key, value in listDict.items():
        arrLists.append(DBList(key = key, QObject = value['list'], description = value['description'].strip('.'))) # prepare a nice list thing.
        
    arrLists.sort(reverse=True) 

    return (render_to_response('users/create_list.html', request, None, {'lists': arrLists}), False) # No, we didn't find it yet...


def search_for_user(request, user_type='Any', extra='', returnList = False):
	""" Interface to search for a user. If you need a user, just use this.
	  Returns (user or response, user returned?) """

	users = None
	error = False
	QSUsers = None


	# Get the "base list" consisting of all the users of a specific type, or all the users.
	if type(user_type) != str:
		All_Users = user_type
	elif user_type == 'All':
		All_Users = ESPUser.objects.all()
	else:
		if user_type not in ESPUser.getTypes():
                    raise ESPUser(), 'user_type must be one of '+str(ESPUser.getTypes())

		All_Users = ESPUser.getAllOfType(user_type, False)

        kwargs = {}
        kwargs_exclude = {}
	if request.GET.has_key('userid') and len(request.GET['userid'].strip()) > 0:
            userid = -1
            try:
                userid = int(request.GET['userid'])
            except:
                raise ESPError(False), 'User id invalid, please enter a number.'

            if request.GET.has_key('userid__not'):
                kwargs_exclude = {'id': userid}
            else:
                kwargs = {'id': userid}

        else:
            for field in ['username','last_name','first_name', 'email']:
                if request.GET.has_key(field) and len(request.GET[field].strip()) > 0:
                    if request.GET.has_key('%s__not' % field):
                        kwargs_exclude.update({'%s__iregex' % field: request.GET[field]})
                    else:
                        kwargs.update({'%s__iregex' % field: request.GET[field]})
        
	if len(kwargs) == 0 and len(kwargs_exclude) == 0:
		users = None
	else:
            #assert False, kwargs
            QSUsers = All_Users
            if len(kwargs) > 0:
                QSUsers = QSUsers.filter(**kwargs)
            if len(kwargs_exclude) > 0:
                QSUsers = QSUsers.exclude(**kwargs_exclude)

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

            if request.GET.has_key('listokay') and request.GET['listokay'] == 'true':
                Q_Filter = False
                if len(kwargs) > 0:
                    Q_Filter = Q(**kwargs)
                if len(kwargs_exclude) > 0:
                    if type(Q_Filter) == Q:
                        Q_Filter = Q_Filter & QNot(Q(**kwargs_exclude))
                    else:
                        Q_Filter = QNot(Q(**kwargs_exclude))
                        
                return (Q_Filter, True)
            
            context = {'users': users, 'extra':str(extra), 'list': returnList}

            return (render_to_response('users/userpick.html', request, None, context), False)
