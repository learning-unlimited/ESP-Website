
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
from esp.datatree.models import DataTree, PermToString, GetNode, StringToPerm
#from peak.api import security, binding
from esp.workflow.models import Controller
from datetime import datetime
from esp.db.models import Q, qlist
from esp.dblog.models import error
from django.db.models.query import QuerySet
from esp.lib.EmptyQuerySet import EMPTY_QUERYSET
from django.core.cache import cache
from datetime import datetime
from esp.middleware import ESPError
from django.template.defaultfilters import urlencode
from django.contrib.auth import logout, login, authenticate



def user_get_key(user):
    """ Returns the key of the user, regardless of anything about the user object. """
    if user is None or type(user) == AnonymousUser or \
         (type(user) != User and type(user) != ESPUser) or \
         user.id is None:
        return 'None'
    else:
        return str(user.id)

def userBitCacheTime():
    return 300


class ESPUser(User, AnonymousUser):
    """ Create a user of the ESP Website
    This user extends the auth.User of django"""

    # this will allow a casting from User to ESPUser:
    #      foo = ESPUser(bar)   <-- foo is now an ``ESPUser''
    def __init__(self, userObj):
        if type(userObj) == ESPUser:
            self.__dict__ = userObj.__dict__
            self.__olduser = userObj.__olduser
        else:
            self.__dict__ = userObj.__dict__
            self.__olduser = userObj            

    def getOld(self):
        if not self.__olduser:
            self.__olduser = User()
        self.__olduser.__dict__ = self.__dict__
        return self.__olduser

    def name(self):
        return '%s %s' % (self.first_name, self.last_name)

    def __cmp__(self, other):
        lastname = cmp(self.last_name.upper(), other.last_name.upper())
        if lastname == 0:
           return cmp(self.first_name.upper(), other.first_name.upper())
        return lastname

    def is_authenticated(self):
        return self.getOld().is_authenticated()

    def getVisible(self, objType):
        return UserBit.find_by_anchor_perms(objType, self, GetNode('V/Flags/Public'))

    def getLastProfile(self):
        from esp.program.models import RegistrationProfile
        return RegistrationProfile.getLastProfile(self)
        
    def getEditable(self, objType):
        return UserBit.find_by_anchor_perms(objType, self, GetNode('V/Administer/Edit'))

    def canEdit(self, object):
        return UserBit.UserHasPerms(self, object.anchor, GetNode('V/Administer/Edit'), datetime.now())

    def updateOnsite(self, request):
        if 'user_morph' in request.session:
            if request.session['user_morph']['onsite'] == True:
                self.onsite_local = True
                self.other_user   = True
                self.onsite_retTitle = request.session['user_morph']['retTitle']
                return True
            elif request.session['user_morph']['olduser'] is not None:
                self.other_user = True
                return False
        else:
            self.onsite_local = False
            self.other_user   = False
            return False


    def switch_to_user(self, request, user, retUrl, retTitle, onsite = False):
        user_morph = {'olduser' : self,
                      'retUrl'  : retUrl,
                      'retTitle': retTitle,
                      'onsite'  : onsite}

        request.session['user_morph'] = user_morph

        if type(user) == ESPUser:
            user = user.getOld()
            
        logout(request)
        
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        
        login(request, user)

    def get_old(self, request):
        if not 'user_morph' in request.session:
            return False
        return request.session['user_morph']['olduser']

    def switch_back(self, request):
        if not 'user_morph' in request.session:
            raise ESPError(), 'Error: You were not another user to begin with!'

        retUrl   = request.session['user_morph']['retUrl']
        new_user = request.session['user_morph']['olduser']
        
        del request.session['user_morph']
        
        logout(request)

        if type(new_user) == ESPUser:
            old_user = new_user.getOld()
            
        old_user.backend = 'django.contrib.auth.backends.ModelBackend'
        
        login(request, old_user)

        return retUrl
        

    def get_msg_vars(self, otheruser, key):
        """ This function will be called when rendering a message. """
        
        if key == 'name':
            return ESPUser(otheruser).name()
        elif key == 'recover_url':
            return 'http://esp.mit.edu/myesp/recoveremail/?code=%s' % \
                         otheruser.password
            
        return ''
    
    def getTaughtClasses(self, program = None):
        """ Return all the taught classes for this user. If program is specified, return all the classes under
            that class. For most users this will return an empty queryset. """
        
        from esp.program.models import Class, Program # Need the Class object.
        all_classes = UserBit.find_by_anchor_perms(Class, self.getOld(), GetNode('V/Flags/Registration/Teacher'))
        
        if program is None: # If we have no program specified
            return all_classes
        else:
            if type(program) != Program: # if we did not receive a program
                error("Expects a real Program object. Not a `"+str(type(program))+"' object.")
            else:
                return all_classes.filter(parent_program = program)


    def getUserNum(self):
        """ Returns the "number" of a user, which is distinct from id.
            It's like the index if you search by lsat and first name."""
        
        users = User.objects.filter(last_name__iexact = self.last_name,
                                    first_name__iexact = self.first_name).order_by('id')
        i = 0
        for user in users:
            if user.id == self.id:
                break
            i += 1
            
        return (i and i or '')

    @staticmethod
    def getUserFromNum(first, last, num):
        if num == '':
            num = 0
        try:
            num = int(num)
        except:
            raise ESPError(), 'Could not find user "%s %s"' % (first, last)
            
        users = User.objects.filter(last_name__iexact = last,
                                    first_name__iexact = first).order_by('id')
        if len(users) <= num:
            raise ESPError(), 'Could not find user "%s %s"' % (first, last)
        
        return ESPUser(users[num])
        
    @staticmethod
    def getTypes():
        """ Get a list of the different roles an ESP user can have. By default there are four rols,
            but there can be more. (Returns ['Student','Teacher','Educator','Guardian']. """
        
        return ['Student','Teacher','Educator','Guardian']

    @staticmethod
    def getAllOfType(strType, QObject = True):
        now = datetime.now()
        Q_after_start = Q(userbit__startdate__isnull = True) | Q(userbit__startdate__lte = now)
        Q_before_end = Q(userbit__enddate__isnull = True) | Q(userbit__enddate__gte = now)

        types = ['Student', 'Teacher','Guardian','Educator']

        if strType not in types:
            raise ESPError(), "Invalid type to find all of."
                
        Q_useroftype      = Q(userbit__verb = GetNode('V/Flags/UserRole/'+strType)) &\
                            Q(userbit__qsc = GetNode('Q'))                          &\
                            Q_after_start                                  &\
                            Q_before_end

        if QObject:
            return Q_useroftype

        else:
            return User.objects.filter(Q_useroftype)


    def getEnrolledClasses(self):
        from esp.program.models import Class
        Conf = UserBit.find_by_anchor_perms(Class, self, GetNode('V/Flags/Registration/Confirmed'))
        Prel = UserBit.find_by_anchor_perms(Class, self, GetNode('V/Flags/Registration/Preliminary'))

        return (Conf | Prel).distinct()

    def isEnrolledInClass(self, clsObj):
        return UserBit.UserHasPerms(self, clsObj.anchor, GetNode('V/Flags/Registration/Confirmed')) or \
               UserBit.UserHasPerms(self, clsObj.anchor, GetNode('V/Flags/Registration/Preliminary'))
        
    def canAdminister(self, nodeObj):
        return UserBit.UserHasPerms(self, nodeObj.anchor, GetNode('V/Administer'))

    def isOnsite(self, program = None):
        verb = GetNode('V/Registration/OnSite')
        if program is None:
            return (hasattr(self, 'onsite_local') and self.onsite_local is True) or \
                    UserBit.bits_get_qsc(user=self, verb=verb).count() > 0
        
        else:
            return UserBit.UserHasPerms(self, program.anchor, verb)

    def recoverPassword(self):
        # generate the code, send the email.
        
        import string
        import random
        from esp.users.models import PersistentQueryFilter
        from esp.db.models import Q
        from esp.dbmail.models import MessageRequest
        from django.template import loader, Context
        
        
        symbols = string.ascii_uppercase + string.digits 
        code = "".join([random.choice(symbols) for x in range(30)])
        
        # get the filter object
        filterobj = PersistentQueryFilter.getFilterFromQ(Q(id = self.id),
                                                         User,
                                                         'User %s' % self.username)
        
        curuser = User.objects.get(id = self.id)
        
        curuser.password = code
        curuser.save()
			
        # create the variable modules
        variable_modules = {'user': ESPUser(curuser)}


        newmsg_request = MessageRequest.createRequest(var_dict   = variable_modules,
                                                      subject    = '[ESP] Your Password Recovery For esp.mit.edu',
                                                      recipients = filterobj,
                                                      sender     = '"MIT Educational Studies Program" <esp@mit.edu>',
                                                      creator    = self,
                                                      msgtext    = loader.find_template_source('email/password_recover')[0])

        newmsg_request.save()



    def isAdministrator(self, program = None):
        if program is None:
            return UserBit.bits_get_qsc(user=self, verb=GetNode("V/Administer")).count() > 0
        else:
            return UserBit.UserHasPerms(self, program.anchor, GetNode('V/Administer'))

    isAdmin = isAdministrator

    def delete(self):
        for x in self.userbit_set.all():
            x.delete()
        super(ESPUser, self).delete()
        
    
    def isTeacher(self):
        """Returns true if this user is a teacher"""
        return UserBit.UserHasPerms(self, GetNode('Q'), GetNode('V/Flags/UserRole/Teacher'))

    def isGuardian(self):
        """Returns true if this user is a teacher"""
        return UserBit.UserHasPerms(self, GetNode('Q'), GetNode('V/Flags/UserRole/Guardian'))

    def isEducator(self):
        """Returns true if this user is a teacher"""
        return UserBit.UserHasPerms(self, GetNode('Q'), GetNode('V/Flags/UserRole/Educator'))


    def isStudent(self):
        """Returns true if this user is a teacher"""
        return UserBit.UserHasPerms(self, GetNode('Q'), GetNode('V/Flags/UserRole/Student'))

    def canEdit(self, nodeObj):
        """Returns True or False if the user can edit the node object"""
        # Axiak
        return UserBit.UserHasPerms(self, nodeObj.anchor, GetNode('V/Administer/Edit'))

    def getMiniBlogEntries(self):
        """Return all miniblog posts this person has V/Subscribe bits for"""
        # Axiak 12/17
        from esp.miniblog.models import Entry
        return UserBit.find_by_anchor_perms(Entry, self, GetNode('V/Subscribe')).order_by('-timestamp')

    @staticmethod
    def isUserNameTaken(username):
        return User.objects.filter(username=username.lower()).count() > 0

    @staticmethod
    def current_schoolyear():
        now = datetime.now()
        curyear = now.year
        if datetime(curyear, 7, 1) > now:
            schoolyear = curyear
        else:
            schoolyear = curyear + 1

        return schoolyear

    def getGrade(self, program = None):
        if not self.isStudent():
            return 0
        if program is None:
            regProf = self.getLastProfile()
        else:
            from esp.program.models import RegistrationProfile
            regProf = RegistrationProfile.getLastForProgram(self,program)
        if regProf and regProf.student_info:
            if regProf.student_info.graduation_year:
                return ESPUser.gradeFromYOG(regProf.student_info.graduation_year)

        return 0

    def currentSchoolYear(self):
        return ESPUser.current_schoolyear()-1

    @staticmethod
    def gradeFromYOG(yog):
        schoolyear = ESPUser.current_schoolyear()
        try:
            yog        = int(yog)
        except:
            return 0
        
        return schoolyear + 12 - yog
    
    @staticmethod
    def YOGFromGrade(grade):
        schoolyear = ESPUser.current_schoolyear()
        try:
            grade = int(grade)
        except:
            return 0

        return schoolyear + 12 - grade      
        
   

class UserBit(models.Model):
    """ Grant a user a bit on a Q """
    user = models.ForeignKey(User, blank=True, null=True) # User to give this permission
    qsc = models.ForeignKey(DataTree, related_name='userbit_qsc') # Controller to grant access to
    verb = models.ForeignKey(DataTree, related_name='userbit_verb') # Do we want to use Subjects?

    startdate = models.DateTimeField(blank=True, null=True)
    enddate = models.DateTimeField(blank=True, null=True)

    recursive = models.BooleanField(default=True)

    def __str__(self):
        curr_user = '?'
        curr_qsc = '?'
        curr_verb = '?'

        try:
            if self.user is None:
                curr_user = 'Everyone'
            else:
                curr_user = str(self.user)
        except Exception:
            pass

        try:
            curr_qsc = PermToString(self.qsc.tree_encode())
        except Exception:
            pass

        try:
            curr_verb = PermToString(self.verb.tree_encode())
        except Exception:
            pass

        if self.recursive:
            recurse = ""
        else:
            recurse = " (non-recursive)"
        
        if self.startdate != None and self.enddate != None:
            return 'GRANT ' + curr_user + ' ' + curr_verb + ' ON ' + curr_qsc + ' <' + str(self.startdate) + ' - ' + str(self.enddate) + '>' + recurse
        else:
            return 'GRANT ' + curr_user + ' ' + curr_verb + ' ON ' + curr_qsc + recurse

    def save(self):
        if self.user is None or type(self.user) == AnonymousUser \
              or (type(self.user) != ESPUser and type(self.user) != User) \
              or self.user.id is None:
            UserBit.updateCache(None)
        else:
            UserBit.updateCache(self.user.id)

        if self.startdate is None or self.startdate == '':
            self.startdate = datetime.now()

        super(UserBit, self).save()

        UserBitImplication.addUserBit(self) # follow implications
        
    def delete(self):
        if self.user is None or type(self.user) == AnonymousUser \
              or (type(self.user) != ESPUser and type(self.user) != User) \
              or self.user.id is None:
            UserBit.updateCache(None)
        else:
            UserBit.updateCache(self.user.id)

        super(UserBit, self).delete()
        
        UserBitImplication.deleteUserBit(self) #follow implications

    @staticmethod
    def updateCache(user_id):
        """ Purges all userbit-related cache associated with user_id or everyone if None. """
        if user_id is None:
            user_ids = [ userid['id'] for userid in User.objects.values('id') ]
            user_ids.append('None')
        else:
            user_ids = [user_id]

        for userid in user_ids:
            # delete the cache
            cache.delete('UserBit__' + str(userid))
        

        

    @staticmethod
    def UserHasPerms(user, qsc, verb, now = None):
        """ Given a user, a permission, and a subject, return True if the user, or all users, has been Granted [subject] on [permission]; False otherwise """
        # aseering: This reeks of code redundancy; is there a way to combine the above and below loops into a single loop?
        # aseering 1-11-2007: Even better; single query!

        if now == None:
            now = datetime.now()
            now_id = "None"
        else:
            now_id = "-".join([ str(i) for i in datetime.now().timetuple() ])

        if type(qsc) == int:
            qsc_id = qsc
        else:
            qsc_id = qsc.id

        if type(verb) == int:
            verb_id = verb
        else:
            verb_id = verb.id

        user_cache_id = 'UserHasPerms:' + str(qsc_id) + ',' + str(verb_id) + ',' + now_id

        cache_id = 'UserBit__' + user_get_key(user)

        userbit_cache = cache.get(cache_id)

        if type(userbit_cache) == dict:
            if userbit_cache.has_key(user_cache_id):
                return userbit_cache[user_cache_id]
        else:
            userbit_cache = {}

        # Filter by user
        if user != None and user.is_authenticated():
            Q_user_correct = Q(user__isnull = True) | Q(user = user)
        else:
            Q_user_correct = Q(user__isnull=True)

        # Filter by date/time range
        Q_date_correct = (Q(startdate__isnull=True) | Q(startdate__lte=now)) & \
                         (Q(enddate__isnull=True) | Q(enddate__gt=now))

        # filter by qsc and verb
        # these ids make bad inner joins go away
        # in django 1.0, replace with OUTER JOINS!
        qsc_parent_ids      = [qsc.id ] + [x['id'] for x in  qsc.antecedents(False).values('id')]
        verb_parent_ids     = [verb.id] + [x['id'] for x in verb.antecedents(False).values('id')]

        Q_recursive_search = Q(recursive = True) & Q(qsc__in = qsc_parent_ids) & Q(verb__in = verb_parent_ids)

        Q_flat_userbit     = Q(qsc = qsc) & Q(verb = verb)


        # the final query:
        num = UserBit.objects.filter(Q_user_correct & Q_date_correct).filter(Q_recursive_search | Q_flat_userbit).count()
        # If we have at least one UserBit meeting these criteria, we have perms.

        retVal = (num > 0)

        userbit_cache[user_cache_id] = retVal
        
        cache.set(cache_id, userbit_cache, userBitCacheTime())

        return retVal
    
    # FIXME: This looks like it has been subject to extreme code rot
    @staticmethod
    def enforce_bits(controller_class, user):
        def call(proc, *args):
            """ Accepts a 'run' function, its associated Controller class (is there a way to getthat information automatically, from the function?), and a user; returns a function that runs the 'run' function and returns 'true' if the user can access this Controller class, and returns 'false' otherwise. """
            proc(args)
            return True

        if UserBit.objects.filter(permission__controller=controller_class.__name__).filter(user_pk=user.id).count() != 0:
            return decorator(call)
        else:
            return lambda : False

    @staticmethod
    def bits_get_users(qsc, verb, now = datetime.now(), end_of_now = None):
        """ Return all users who have been granted 'verb' on 'qsc'
           Note that this requires the Q objects to work correctly. """
        if end_of_now == None: end_of_now = now
            
        Q_recursive      = Q(recursive = True)
        Q_verb_recursive = Q(verb__rangestart__lte = verb.rangestart) & Q(verb__rangeend__gte = verb.rangeend)
        Q_qsc_recursive  = Q(qsc__rangestart__lte  = qsc.rangestart)  & Q(qsc__rangeend__gte  = qsc.rangeend )

        Q_exact_match    = Q(verb = verb.id) & Q(qsc = qsc.id) # & Q(recursive = False), not needed

        Q_recursive_search = Q_verb_recursive & Q_qsc_recursive & Q_recursive

        Q_after_start = Q(startdate__isnull = True) | Q(startdate__lte = end_of_now)
        Q_before_end = Q(enddate__isnull = True) | Q(enddate__gte = now)
		
        userbits = UserBit.objects.filter(Q_after_start & Q_before_end).filter(Q_recursive_search | Q_exact_match)

        return userbits.distinct()
    

    @staticmethod
    def bits_get_qsc(user, verb, now = True, end_of_now = None, qsc_root=None):
        """  Return all qsc structures to which 'user' has been granted 'verb'

        If 'qsc_root' is specified, only return qsc structures at or below the specified node """
        user_cache_id = 'bit_get_qsc:' + str(verb.id) + ',' + str(now) + ',' + str(end_of_now) + ',' + str(qsc_root)

        cache_id = 'UserBit__' + user_get_key(user)

        userbit_cache = cache.get(cache_id)

        usedCache = False
        if type(userbit_cache) == dict:
            if userbit_cache.has_key(user_cache_id):
                usedCache = True
                userbits  = userbit_cache[user_cache_id]
        else:
            userbit_cache = {}

        if now == True:
            now = datetime.now()

        # the cache hasn't been used
        if not usedCache:
            if end_of_now == None: end_of_now = now

            # this should make sense...we're going to recursively search

            #first we make sure the verbs are correct
            Q_verb_recursive = Q(recursive = True) & \
                               Q(verb__rangestart__lte = verb.rangestart) & \
                               Q(verb__rangeend__gte = verb.rangeend)
            
            Q_exact_match    = Q(verb = verb)

            # now we make sure the dates are correct
            Q_after_start = Q(startdate__isnull = True) | Q(startdate__lte = end_of_now)
            Q_before_end = Q(enddate__isnull = True) | Q(enddate__gte = now)
		
            # and now we make sure the user is correct
            Q_correct_user = Q(user__isnull = True)
            if user is not None and user.is_authenticated():
                Q_correct_user |= Q(user = user.id)

            # now we put it all together
            qscs = UserBit.objects.filter(Q_correct_user & Q_after_start & Q_before_end & (Q_verb_recursive | Q_exact_match))
            # now we have to filter for the root
            if qsc_root is None:
                userbits = qlist(qscs)
            else:
                Q_under_root = Q(qsc__rangestart__gte = qsc_root.rangestart) & \
                               Q(qsc__rangeend__lte   = qsc_root.rangeend)

                
                userbits = qlist(qscs.filter(Q_under_root).distinct())

            # we're saving the cache: N.B. if we don't use list() on it first, we
            # might be saving the lazy'd query, and not the db work!
            userbit_cache[user_cache_id] = userbits
            
        cache.set(cache_id, userbit_cache, userBitCacheTime())
        
        return userbits


    @staticmethod
    def bits_get_verb(user, qsc, now = None, end_of_now = None):
        """ Return all verbs that 'user' has been granted on 'qsc' """
        user_cache_id = 'bit_get_verb:' + str(user.id) + ',' + str(now) + ',' + str(end_of_now) + ',' + str(qsc.id)

        cache_id = 'UserBit__' + user_get_key(user)

        userbit_cache = cache.get(cache_id)

        usedCache = False
        if type(userbit_cache) == dict:
            if userbit_cache.has_key(user_cache_id):
                usedCache = True
                userbits  = userbit_cache[user_cache_id]
        else:
            userbit_cache = {}

        if now is None:
            now = datetime.now()

        # the cache hasn't been used
        if not usedCache:
            if end_of_now == None: end_of_now = now

            # this should make sense...we're going to recursively search

            #first we make sure the verbs are correct
            Q_qsc_recursive = Q(recursive = True) & \
                              Q(qsc__rangestart__lte = qsc.rangestart) & \
                              Q(qsc__rangeend__gte = qsc.rangeend)
            
            Q_exact_match    = Q(qsc = qsc)

            # now we make sure the dates are correct
            Q_after_start = Q(startdate__isnull = True) | Q(startdate__lte = end_of_now)
            Q_before_end = Q(enddate__isnull = True) | Q(enddate__gte = now)
		
            # and now we make sure the user is correct
            Q_correct_user = Q(user__isnull = True)
            if user is not None and user.is_authenticated():
                Q_correct_user |= Q(user = user.id)

            # now we put it all together
            userbits = qlist(UserBit.objects.filter(Q_correct_user & Q_after_start & Q_before_end & (Q_qsc_recursive | Q_exact_match)))


            # we're saving the cache: N.B. if we don't use list() on it first, we
            # might be saving the lazy'd query, and not the db work!
            userbit_cache[user_cache_id] = userbits
            
        cache.set(cache_id, userbit_cache, userBitCacheTime())
        
        return userbits
        

    @staticmethod
    def has_bits(queryset):
        """ Returns False if there are no elements in queryset """
        return ( queryset.count() > 0 )

    @staticmethod
    def find_by_anchor_perms(module,user,verb,qsc=None):
    	""" Fetch a list of relevant items for a given user and verb in a module that has an anchor foreign key into the DataTree """
    	#q_list = [ x.qsc for x in UserBit.bits_get_qsc( user, verb ) ]
        q_list = UserBit.bits_get_qsc( user, verb )
    	# Extract entries associated with a particular branch

        res = None

        for bit in q_list:
            q = bit.qsc

            if bit.recursive:
                qsc_children_ids = [q.id] + [x['id'] for x in q.descendants(False).values('id')]
                query = module.objects.filter(anchor__in = qsc_children_ids)
            else:
                query = module.objects.filter(anchor=q)
                
            if qsc is not None:
                query = query.filter(anchor__rangestart__gte=qsc.rangestart, anchor__rangeend__lte=qsc.rangeend)

            if res == None:
                res = query
            else:
                res = res | query

        if res != None:
            res = res.distinct()

        if res == None:
            return module.objects.filter(id=-1).distinct()

	# Operation Complete!
	return res

    class Admin:
        pass

    
class StudentInfo(models.Model):
    """ ESP Student-specific contact information """
    user = models.ForeignKey(User, blank=True, null=True)
    graduation_year = models.PositiveIntegerField(blank=True, null=True)
    school = models.CharField(maxlength=256,blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    studentrep = models.BooleanField(blank=True, null=True, default = False)
    
    def updateForm(self, form_dict):
        form_dict['graduation_year'] = self.graduation_year
        form_dict['school']          = self.school
        form_dict['dob']             = self.dob
        return form_dict        

    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a StudentInfo record """
        if regProfile.student_info is None:
            studentInfo = StudentInfo()
            studentInfo.user = curUser
        else:
            studentInfo = regProfile.student_info
        
        studentInfo.graduation_year = new_data['graduation_year']
        studentInfo.school          = new_data['school']
        studentInfo.dob             = new_data['dob']
        studentInfo.save()
        return studentInfo
    
    def __str__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Student Info (%s)' % username
            
    class Admin:
        pass

class TeacherInfo(models.Model):
    """ ESP Teacher-specific contact information """
    user = models.ForeignKey(User, blank=True, null=True)
    graduation_year = models.PositiveIntegerField(blank=True, null=True)
    college = models.CharField(maxlength=128,blank=True, null=True)
    major = models.CharField(maxlength=32,blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    
    def updateForm(self, form_dict):
        form_dict['graduation_year'] = self.graduation_year
        form_dict['school']          = self.college
        form_dict['major']           = self.major
        form_dict['dob']             = self.dob
        return form_dict
    
    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a TeacherInfo record """
        if regProfile.teacher_info is None:
            teacherInfo = TeacherInfo()
            teacherInfo.user = curUser
        else:
            teacherInfo = regProfile.teacher_info
        
        teacherInfo.graduation_year = new_data['graduation_year']
        teacherInfo.college         = new_data['school']
        teacherInfo.major           = new_data['major']
        teacherInfo.dob           = new_data['dob']
        
        teacherInfo.save()
        return teacherInfo
                    
    def __str__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Teacher Info (%s)' % username

    class Admin:
        pass
    
class GuardianInfo(models.Model):
    """ ES Guardian-specific contact information """
    user = models.ForeignKey(User, blank=True, null=True)
    year_finished = models.PositiveIntegerField(blank=True, null=True)
    num_kids = models.PositiveIntegerField(blank=True, null=True)

    def updateForm(self, form_dict):
        form_dict['year_finished'] = self.year_finished
        form_dict['num_kids']      = self.num_kids
        return form_dict
    
    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a GuardianInfo record """
        if regProfile.guardian_info is None:
            guardianInfo = GuardianInfo()
            guardianInfo.user = curUser
        else:
            guardianInfo = regProfile.guardian_info
        
        guardianInfo.year_finished = new_data['year_finished']
        guardianInfo.num_kids      = new_data['num_kids']
        guardianInfo.save()
        return guardianInfo
    
    def __str__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Guardian Info (%s)' % username
    
    class Admin:
        pass

class EducatorInfo(models.Model):
    """ ESP Educator-specific contact information """
    user = models.ForeignKey(User, blank=True, null=True)
    subject_taught = models.CharField(maxlength=64,blank=True, null=True)
    grades_taught = models.CharField(maxlength=16,blank=True, null=True)
    school = models.CharField(maxlength=128,blank=True, null=True)
    position = models.CharField(maxlength=64,blank=True, null=True)
    
    def updateForm(self, form_dict):
        form_dict['subject_taught'] = self.subject_taught
        form_dict['grades_taught']  = self.grades_taught
        form_dict['school']         = self.school
        form_dict['position']       = self.position        
        return form_dict
    
    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a EducatorInfo record """
        if regProfile.educator_info is None:
            educatorInfo = EducatorInfo()
            educatorInfo.user = curUser
        else:
            educatorInfo = regProfile.educator_info
        
        educatorInfo.subject_taught = new_data['subject_taught']
        educatorInfo.grades_taught  = new_data['grades_taught']
        educatorInfo.position       = new_data['position']      
        educatorInfo.school         = new_data['school']
        educatorInfo.save()
        return educatorInfo
        
    def __str__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Educator Info (%s)' % username

    
    class Admin:
        pass

class ZipCode(models.Model):
    """ Zip Code information """
    zip_code = models.CharField(maxlength=5)
    latitude = models.FloatField(max_digits=10, decimal_places = 6)
    longitude = models.FloatField(max_digits=10, decimal_places = 6)

    def distance(self, other):
        """ Returns the distance from one point to another """
        import math

        earth_radius = 3963.1676 # From google...
        
        lat1 = math.radians(self.latitude)
        lon1 = math.radians(self.longitude)
        lat2 = math.radians(other.latitude)
        lon2 = math.radians(other.longitude)

        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1

        tmp = math.sin(delta_lat/2.0)**2 + \
              math.cos(lat1)*math.cos(lat2) * \
              math.sin(delta_lon/2.0)**2

        distance = 2 * math.atan2(math.sqrt(tmp), math.sqrt(1-tmp)) * \
                   earth_radius

        return distance
    
    def close_zipcodes(self, distance):
        """ Get a list of zip codes less than or equal to
            distance from this zip code. """

        try:
            distance = float(distance)
        except:
            raise ESPError(), '%s should be a valid number!' % distance

        if distance < 0:
            distance *= -1

        oldsearches = ZipCodeSearches.objects.filter(zip_code = self,
                                                     distance = distance)

        if len(oldsearches) > 0:
            return oldsearches[0].zipcodes.split(',')
                                             
        
        all_zips = list(ZipCode.objects.exclude(id = self.id))
        winners  = [ self.zip_code ]

        winners += [ zipc.zip_code for zipc in all_zips
                     if self.distance(zipc) <= distance ]

        newsearch = ZipCodeSearches(zip_code = self,
                                    distance = distance,
                                    zipcodes = ','.join(winners))
        newsearch.save()
        
        return winners

    def __str__(self):
        return '%s (%s, %s)' % (self.zip_code,
                                self.longitude,
                                self.latitude)

class ZipCodeSearches(models.Model):
    zip_code = models.ForeignKey(ZipCode)
    distance = models.FloatField(max_digits = 15, decimal_places = 3)
    zipcodes = models.TextField()

    def __str__(self):
        return '%s Zip Codes that are less than %s miles from %s' % \
               (len(self.zipcodes.split(',')), self.distance, self.zip_code)

class ContactInfo(models.Model):
	""" ESP-specific contact information for (possibly) a specific user """
	user = models.ForeignKey(User, blank=True, null=True)
	first_name = models.CharField(maxlength=64)
	last_name = models.CharField(maxlength=64)        
	e_mail = models.EmailField(blank=True, null=True)
	phone_day = models.PhoneNumberField(blank=True, null=True)
	phone_cell = models.PhoneNumberField(blank=True, null=True)
	phone_even = models.PhoneNumberField(blank=True, null=True)
	address_street = models.CharField(maxlength=100,blank=True, null=True)
	address_city = models.CharField(maxlength=50,blank=True, null=True)
	address_state = models.USStateField(blank=True, null=True)
	address_zip = models.CharField(maxlength=5,blank=True, null=True)

        def address(self):
            return '%s, %s, %s %s' % \
                   (self.address_street,
                    self.address_city,
                    self.address_state,
                    self.address_zip)
                    

        def items(self):
            return self.__dict__.items()

        @staticmethod
        def addOrUpdate(regProfile, new_data, contactInfo, prefix='', curUser=None):
            """ adds or updates a ContactInfo record """
            if contactInfo is None:
                contactInfo = ContactInfo()
            for i in contactInfo.__dict__.keys():
                if i != 'user_id' and i != 'id' and new_data.has_key(prefix+i):
                    contactInfo.__dict__[i] = new_data[prefix+i]
            if curUser is not None:
                contactInfo.user = curUser
            contactInfo.save()
            return contactInfo

        def updateForm(self, form_data, prepend=''):
            newkey = self.__dict__
            for key, val in newkey.items():
                if val and key != 'id':
                    form_data[prepend+key] = str(val)

            return form_data
        
	def __str__(self):
            username = ""
            last_name, first_name = '', ''
            if self.user != None:
                username = self.user.username
            if self.first_name is not None:
                first_name = self.first_name
            if self.last_name is not None:
                last_name = self.last_name
            return first_name + ' ' + last_name + ' (' + username + ')'
	
	class Admin:
		pass

def GetNodeOrNoBits(nodename, user = AnonymousUser(), verb = None):
    """ Get the specified node.  Create it only if the specified user has create bits on it """
    if user == None or not user.is_authenticated():
        user_id = "None"
    else:
        user_id = user.username

    if verb == None:
        verb_id = "None"
    else:
        verb_id = str(verb.id)

    cache_id = 'datatree:' + user_id + ',' + str(verb_id) + ',' + nodename

    cached_val = cache.get(urlencode(cache_id))
    if cached_val != None:
        return cached_val

    nodes = DataTree.objects.filter(name='ROOT', parent__isnull=True)
    node = None
    if nodes.count() < 1L:
        error("Trying to create a new root node here.  Dying...")
        assert False, "Trying to create a new root node here.  Dying..."
        node = DataTree()
        node.name = 'ROOT'
        node.parent = None
        node.save()
    elif nodes.count() == 1L:
        node = nodes[0]
    else:
        raise DataTree.NoRootNodeException(nodes.count())
    
    perm = StringToPerm(nodename)
    if nodename == '':
        perm = []

    try:
        retVal = node.tree_decode(perm)

        if retVal.id == -1:
            pass

        cache.set(urlencode(cache_id), retVal)
        return retVal
    except DataTree.NoSuchNodeException, e:
        if verb == None:
            verb = GetNode("V/Administer/Program/Class")

        if UserBit.UserHasPerms(user, e.anchor, verb):
            retVal = e.anchor.tree_create(e.remainder)

            if retVal.id == -1:
                pass

            cache.set(urlencode(cache_id), retVal)
            return retVal
        else:
            raise

class PersistentQueryFilter(models.Model):
    """ This class stores generic query filters persistently in the database, for retrieval (by ID, presumably) and
        to pass the query along to multiple pages and retrival (et al). """
    
    item_model   = models.CharField(maxlength=256)            # A string representing the model, for instance User or Program
    q_filter     = models.TextField()                         # A string representing a query filter
    sha1_hash    = models.CharField(maxlength=256)            # A sha1 hash of the string representing the query filter
    create_ts    = models.DateTimeField(auto_now_add = True)  # The create timestamp
    useful_name  = models.CharField(maxlength=1024, blank=True, null=True) # A nice name to apply to this filter.



    @staticmethod
    def create_from_Q(item_model, q_filter, description = ''):
        """ The main constructor, please call this. """
        
        import pickle
        import sha

        foo = PersistentQueryFilter()
        
        foo.item_model   = str(item_model)
        foo.q_filter     = pickle.dumps(q_filter) # we pickle the q_filter
        foo.sha1_hash    = sha.new(foo.q_filter).hexdigest()

        
        foo.useful_name = description
        return foo
        
        

    def get_Q(self):
        """ This will return the Q object that was passed into it. """
        import pickle

        try:
            QObj = pickle.loads(self.q_filter)
        except:
            raise ESPError(), 'Invalid Q object stored in database.'


        return QObj

    def getList(self, module):
        """ This will actually return the list generated from the filter applied
            to the live database. You must supply the model. If the model is not matched,
            it will become an error. """

        if str(module) != str(self.item_model):
            raise ESPError(), 'The module given does not match that of the persistent entry.'

        return module.objects.filter(self.get_Q())

    @staticmethod
    def getFilterFromID(id, model):
        """ This function will return a PQF object from the id given. """
        try:
            id = int(id)
        except:
            assert False, 'The query filter id given is invalid.'

 
        return PersistentQueryFilter.objects.get(id = id,
                                                 item_model = str(model))
    
 
                


    @staticmethod
    def getFilterFromQ(QObject, model, description = ''):
        """ This function will get the filter from the Q object. It will either create one
            or use an old one depending on whether it's been used. """

        import pickle
        import sha
        
        try:
            qobject_string = pickle.dumps(QObject)
        except:
            qobject_string = ''


        
        try:
            filterObj = PersistentQueryFilter.objects.get(sha1_hash = sha.new(qobject_string).hexdigest())#    pass
        except:
            filterObj = PersistentQueryFilter.create_from_Q(item_model  = model,
                                                            q_filter    = QObject,
                                                            description = description)
            filterObj.save() # create a new one.

        return filterObj

    def __str__(self):
        return str(self.useful_name)
        


class DBList(object):
    """ Useful abstraction for the list of users.
        Not meant for anything but users_get_list...
    """
    totalnum = False # we dont' know how many there are.
    key      = ''
    QObject  = None
    
    
    def count(self, override = False):
        """ This is used to count how many objects wer are talking about.
            If override is true, it will not retrieve the number from cache
            or from this instance. If it's true, it will try.
        """
        
        from esp.users.models import User

        cache_id = urlencode('DBListCount: %s' % (self.key))

        retVal   = cache.get(cache_id) # get the cached result
 
        if self.QObject: # if there is a q object we can just 
            if not self.totalnum:
                if override:
                    self.totalnum = User.objects.filter(self.QObject).distinct().count()
                    cache.set(cache_id, self.totalnum, 60)
                else:
                    cachedval = cache.get(cache_id)
                    if cachedval is None:
                        self.totalnum = User.objects.filter(self.QObject).distinct().count()
                        cache.set(cache_id, self.totalnum, 60)
                    else:
                        self.totalnum = cachedval

            return self.totalnum
        else:
            return 0
        
    def id(self):
        """ The id is the same as the key, it is client-specified. """
        return self.key
    
    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    def __cmp__(self, other):
        """ We are going to order by the size of our lists. """
        return cmp(self.count(), other.count())
    
    def __str__(self):
        return self.key




class UserBitImplication(models.Model):
    """ This model will create implications for userbits...
      that is, if a user has A permission, they will get B """
    
    qsc_original  = models.ForeignKey(DataTree, related_name = 'qsc_original',  blank=True, null=True)
    verb_original = models.ForeignKey(DataTree, related_name = 'verb_original', blank=True, null=True)
    qsc_implied   = models.ForeignKey(DataTree, related_name = 'qsc_implied',   blank=True, null=True)
    verb_implied  = models.ForeignKey(DataTree, related_name = 'verb_implied',  blank=True, null=True)
    recursive     = models.BooleanField(default = True)
    created_bits  = models.ManyToManyField(UserBit, blank=True, null=True)

    def __str__(self):
        var = {}
        for k in ['verb_original_id', 'qsc_original_id',
                  'verb_implied_id',  'qsc_implied_id' ]:
            if getattr(self, k) is None:
                var[k[:-3]] = '*'
            else:
                var[k[:-3]] = str(getattr(self, k[:-3]))
                
        string = '%s on %s ==> %s on %s' % \
                 (var['verb_original'], var['qsc_original'],
                  var['verb_implied'],  var['qsc_implied'])
        
        if self.recursive:
            string += ' (recursive)'
        return string


    @staticmethod
    def get_under_bit(userbit):
        """ Return all implications under a userbit.
        That is, the set of all A ==> B such that A is true
        because of userbit. """
        Q_qsc_null  = Q(qsc_original__isnull = True)
        Q_verb_null = Q(verb_original__isnull = True)
        
        if not userbit.recursive:
            Q_qsc  = Q(qsc_original  = userbit.qsc)
            Q_verb = Q(verb_original = userbit.verb)
        else:
            Q_qsc  = Q(qsc_original__rangestart__gte = userbit.qsc.rangestart,
                       qsc_original__rangeend__lte   = userbit.qsc.rangeend)
            Q_verb = Q(verb_original__rangestart__gte = userbit.verb.rangestart,
                       verb_original__rangeend__lte   = userbit.verb.rangeend)

        # if one of the two are null, the other one can match and it'd be fine.
        Q_match = (Q_qsc & Q_verb) | (Q_qsc_null & Q_verb) | (Q_qsc & Q_verb_null)
        
        return UserBitImplication.objects.filter(Q_match).distinct()
                       

    @staticmethod
    def deleteUserBit(old_userbit):
        """ Delete all the userbits that depended on this one.
            This should be executed *after* a userbit has been deleted.
            (i.e. this should be run from UserBit.delete() 
        """
        implications = UserBitImplication.get_under_bit(old_userbit)

        # first we go through all implications
        for implication in implications:
            # now we get all the bits this implication created
            for bit in implication.created_bits.all():
                # if there is no other way this implication is valid for this user
                # delete...
                if not UserBit.UserHasPerms(user = bit.user,
                                            qsc  = old_userbit.qsc,
                                            verb = old_userbit.verb):
                    bit.delete()
        
        
    def impliedBit(self, originalBit):
        """ Returns the implied userbit if a bit is given. """
        qsc_implied = self.qsc_implied
        verb_implied = self.verb_implied

        if qsc_implied is None:
            qsc_implied = originalBit.qsc
        if verb_implied is None:
            verb_implied = originalBit.verb
        return UserBit(user = originalBit.user,
                       qsc  = qsc_implied,
                       verb = verb_implied,
                       recursive = self.recursive)


    @staticmethod
    def addUserBit(userbit):
        """ This will check to see if the addition of this userbit
            should force other userbits to be created via implications.
        """
        implications = UserBitImplication.get_under_bit(userbit)

        for implication in implications:
            newbit = implication.impliedBit(userbit)

            newbit.save()

            implication.created_bits.add(newbit)
            implication.save()

    def save(self):
        super(UserBitImplication, self).save()

        self.apply()
    
    def delete(self):
        for bit in self.created_bits.all():
            bit.delete()
            
        super(UserBitImplication, self).delete()



    def apply(self):
        " This will generate the userbits for this implication. "
        if self.qsc_original_id is None and self.verb_original_id is None:
            return
        if self.qsc_original_id is not None:
            Q_qsc = (Q(qsc__rangestart__lte = self.qsc_original.rangestart) &\
                     Q(qsc__rangeend__gte   = self.qsc_original.rangeend)   &\
                     Q(recursive       = True)) \
                     | \
                     Q(qsc = self.qsc_original_id)
            
        if self.verb_original_id is not None:
            Q_verb = (Q(verb__rangestart__lte = self.verb_original.rangestart)&\
                      Q(verb__rangeend__gte   = self.verb_original.rangeend)  &\
                      Q(recursive       = True)) \
                      | \
                      Q(verb = self.verb_original_id)

        userbits = UserBit.objects

        if self.qsc_original_id is not None:
            userbits = userbits.filter(Q_qsc)
        if self.verb_original_id is not None:
            userbits = userbits.filter(Q_verb)
        
        
        for userbit in userbits:
            # for each userbit we're going to create the correct
            # corresponding userbits.

            newbit = self.impliedBit(userbit) # get this bit this implies

            bits = UserBit.objects.filter(user = newbit.user,
                                          qsc  = newbit.qsc,
                                          verb = newbit.verb)
            if self.recursive:
                bits.filter(recursive = True)

            if bits.count() == 0:
                newbit.save()
                self.created_bits.add(newbit)
                self.save()
        
    @staticmethod
    def applyAllImplications():
        """ This function will make implications work, no matter what.
          In the entire tree.
        """
        for implication in UserBitImplication.objects.all():
            implication.apply()
    
    class Admin:
        pass

