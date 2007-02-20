""" This is the views portion of the users utility, which has some user-oriented views."""
from esp.middleware   import ESPError
from django.db.models.query import Q, QNot
from esp.users.models import DBList, PersistentQueryFilter, ESPUser, User
from esp.web.util     import render_to_response

def get_user_list(request, listDict):
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

        return (filterObj, True) # We got the list, return it.

    # we're going to prepare a list to send out.
    arrLists = []

    for key, value in listDict.items():
        arrLists.append(DBList(key = key, QObject = value['list'], description = value['description'].strip('.'))) # prepare a nice list thing.
        
    arrLists.sort(reverse=True) 

    return (render_to_response('users/create_list.html', request, None, {'lists': arrLists}), False) # No, we didn't find it yet...
