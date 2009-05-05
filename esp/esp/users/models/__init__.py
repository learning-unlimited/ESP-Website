
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 MIT ESP

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

from datetime import datetime, timedelta

from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.localflavor.us.models import USStateField, PhoneNumberField
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import models
from django.db.models.query import Q, QuerySet
from django.http import HttpRequest
from django.template import Context, loader
from django.template.defaultfilters import urlencode

from esp.cache import cache_function, wildcard
from esp.datatree.models import *
from esp.db.fields import AjaxForeignKey
from esp.db.models.prepared import ProcedureManager
from esp.dblog.models import error
from esp.middleware import ESPError


try:
    import cPickle as pickle
except ImportError:
    import pickle


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

def admin_required(func):
    def wrapped(request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated() or not ESPUser(request.user).isAdministrator():
            raise PermissionDenied
        return func(request, *args, **kwargs)
    return wrapped


class ESPUserManager(ProcedureManager):

    pass

class ESPUser(User, AnonymousUser):
    """ Create a user of the ESP Website
    This user extends the auth.User of django"""

    class Meta:
        app_label = 'auth'
        db_table = 'auth_user'

        def __init__(self):
            super(Meta, self).__init__()
            self.pk.attname = "id"
            self.local_fields[0].column = "id"
        
    objects = ESPUserManager()
    # this will allow a casting from User to ESPUser:
    #      foo = ESPUser(bar)   <-- foo is now an ``ESPUser''
    def __init__(self, userObj, *args, **kwargs):
        if isinstance(userObj, ESPUser):
            self.__olduser = userObj.getOld()
            self.__dict__.update(self.__olduser.__dict__)

        elif isinstance(userObj, (User, AnonymousUser)):
            self.__dict__ = userObj.__dict__
            self.__olduser = userObj

        else:
            User.__init__(self, userObj, *args, **kwargs)
            
        self.other_user = False

    @classmethod
    def ajax_autocomplete(cls, data):
        names = data.strip().split(',')
        last = names[0]

        query_set = cls.objects.filter(last_name__istartswith = last.strip())

        if len(names) > 1:
            first  = ','.join(names[1:])
            if len(first.strip()) > 0:
                query_set = query_set.filter(first_name__istartswith = first.strip())

        values = query_set.order_by('last_name','first_name','id').values('first_name', 'last_name', 'username', 'id')

        for value in values:
            value['ajax_str'] = '%s, %s (%s)' % (value['last_name'], value['first_name'], value['username'])
        return values

    def ajax_str(self):
        return "%s, %s (%s)" % (self.last_name, self.first_name, self.username)

    def getOld(self):
        if not hasattr(self, "_ESPUser__olduser"):
            self.__olduser = User()
        self.__olduser.__dict__.update(self.__dict__)
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
        # caching is handled in RegistrationProfile.getLastProfile
        # for coherence w.r.t clearing and more caching
        from esp.program.models import RegistrationProfile
        return RegistrationProfile.getLastProfile(self)

    @cache_function
    def getEditable_ids(self, objType):
        # As far as I know, fbap's cache is still screwy, so we'll retain this cache at a higher level for now --davidben, 2009-04-06
        return UserBit.find_by_anchor_perms(objType, self, GetNode('V/Administer/Edit')).values_list('id', flat=True)
    getEditable_ids.get_or_create_token(('self',)) # Currently very difficult to determine type, given anchor
    getEditable_ids.depend_on_row(lambda:UserBit, lambda bit: {} if bit.user_id is None else {'self': bit.user},
                                                  lambda bit: bit.applies_to_verb('V/Administer/Edit'))

    def getEditable(self, objType):
        return objType.objects.filter(id__in=self.getEditable_ids(objType))

    def canEdit(self, object):
        return UserBit.UserHasPerms(self, object.anchor, GetNode('V/Administer/Edit'), datetime.now())

    def updateOnsite(self, request):
        if 'user_morph' in request.session:
            if request.session['user_morph']['onsite'] == True:
                self.onsite_local = True
                self.other_user   = True
                self.onsite_retTitle = request.session['user_morph']['retTitle']
                return True
            elif request.session['user_morph']['olduser_id'] is not None:
                self.other_user = True
                return False
        else:
            self.onsite_local = False
            self.other_user   = False
            return False


    def switch_to_user(self, request, user, retUrl, retTitle, onsite = False):
        user_morph = {'olduser_id' : self.id,
                      'retUrl'  : retUrl,
                      'retTitle': retTitle,
                      'onsite'  : onsite}

        if type(user) == ESPUser:
            user = user.getOld()
        logout(request)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        request.session['user_morph'] = user_morph

    def get_old(self, request):
        if not 'user_morph' in request.session:
            return False
        return ESPUser.objects.get(id=request.session['user_morph']['olduser_id'])

    def switch_back(self, request):
        if not 'user_morph' in request.session:
            raise ESPError(), 'Error: You were not another user to begin with!'

        retUrl   = request.session['user_morph']['retUrl']
        new_user = self.get_old(request)
        del request.session['user_morph']
        logout(request)

        if type(new_user) == ESPUser:
            old_user = new_user.getOld()
        old_user.backend = 'django.contrib.auth.backends.ModelBackend'
        
        login(request, old_user)

        return retUrl

    def get_msg_vars(self, otheruser, key):
        """ This function will be called when rendering a message. """
        if key == 'first_name':
            return otheruser.first_name
        elif key == 'last_name':
            return otheruser.last_name
        elif key == 'name':
            return ESPUser(otheruser).name()
        elif key == 'username':
            return otheruser.username
        return ''

    @cache_function
    def getTaughtClasses(self, program = None):
        """ Return all the taught classes for this user. If program is specified, return all the classes under
            that class. For most users this will return an empty queryset. """
        from esp.program.models import ClassSubject, Program # Need the Class object.
        
        #   Why is it that we had a find_by_anchor_perms function again?
        tr_node = GetNode('V/Flags/Registration/Teacher')
        all_classes = ClassSubject.objects.filter(anchor__userbit_qsc__verb__id=tr_node.id, anchor__userbit_qsc__user=self).distinct()
        if program is None: # If we have no program specified
            return all_classes
        else:
            if type(program) != Program: # if we did not receive a program
                error("Expects a real Program object. Not a `"+str(type(program))+"' object.")
            else:
                return all_classes.filter(parent_program = program)
    # FIXME: What if the Program query gives nothing?
    getTaughtClasses.depend_on_row(lambda:UserBit, lambda bit: {'self': bit.user, 'program': Program.objects.get(anchor=bit.qsc.parent.parent)},
                                                    lambda bit: bit.verb_id == GetNode('V/Flags/Registration/Teacher').id)
    # FIXME: depend on ClassSubject (ids vs values thing again)
    #   This one's important... if ClassSubject data changes...
    # kinda works, but a bit too heavy handed:
    getTaughtClasses.depend_on_row(lambda:ClassSubject, lambda cls: {'program': cls.parent_program})


    @cache_function
    def getTaughtSections(self, program = None):
        from esp.program.models import ClassSection
        classes = list(self.getTaughtClasses(program))
        return ClassSection.objects.filter(parent_class__in=classes)
    getTaughtSections.get_or_create_token(('program',))
    # FIXME: Would be REALLY nice to kill it only for the teachers of this section
    # ...key_set specification needs more work...
    getTaughtSections.depend_on_row(lambda:ClassSection, lambda instance: {'program': instance.parent_program})
    getTaughtSections.depend_on_cache(getTaughtClasses, lambda self=wildcard, program=wildcard, **kwargs:
                                                              {'self':self, 'program':program})

    def getTaughtTime(self, program = None, include_scheduled = True):
        """ Return the time taught as a timedelta. If a program is specified, return the time taught for that program.
            If include_scheduled is given as False, we don't count time for already-scheduled classes. """
        user_sections = self.getTaughtSections(program)
        total_time = timedelta()
        for s in user_sections:
            if include_scheduled or (s.start_time() is None):
                total_time = total_time + timedelta(hours=float(s.duration))
        return total_time

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
            raise ESPError(False), '"%s %s": Unknown User' % (first, last)
        return ESPUser(users[num])

    @staticmethod
    def getTypes():
        """ Get a list of the different roles an ESP user can have. By default there are four rols,
            but there can be more. (Returns ['Student','Teacher','Educator','Guardian']. """

        return ['Student','Teacher','Educator','Guardian']

    @staticmethod
    def getAllOfType(strType, QObject = True):
        types = ['Student', 'Teacher','Guardian','Educator']

        if strType not in types:
            raise ESPError(), "Invalid type to find all of."

        Q_useroftype      = Q(userbit__verb = GetNode('V/Flags/UserRole/'+strType)) &\
                            Q(userbit__qsc = GetNode('Q'))                          &\
                            UserBit.not_expired('userbit')

        if QObject:
            return Q_useroftype

        else:
            return User.objects.filter(Q_useroftype)

    @cache_function
    def getAvailableTimes(self, program, ignore_classes=False):
        """ Return a list of the Event objects representing the times that a particular user
            can teach for a particular program. """
        from esp.resources.models import Resource
        from esp.cal.models import Event

        valid_events = Event.objects.filter(resource__user=self, anchor=program.anchor)

        if ignore_classes:
            #   Subtract out the times that they are already teaching.
            other_sections = self.getTaughtSections(program)

            other_times = [sec.meeting_times.values_list('id', flat=True) for sec in other_sections]
            for lst in other_times:
                valid_events = valid_events.exclude(id__in=lst)

        return valid_events
    getAvailableTimes.get_or_create_token(('self', 'program',))
    getAvailableTimes.depend_on_cache(getTaughtSections,
            lambda self=wildcard, program=wildcard, **kwargs:
                 {'self':self, 'program':program, 'ignore_classes':True})
    # FIXME: Really should take into account section's teachers...
    # even though that shouldn't change often
    getAvailableTimes.depend_on_m2m(lambda:ClassSection, 'meeting_times', lambda sec, event: {'program': sec.parent_program})
    getAvailableTimes.depend_on_row(lambda:Resource, lambda resource:
                                        # FIXME: What if resource.event.anchor somehow isn't a program?
                                        # Probably want a helper method return a special "nothing" object (XXX: NOT None)
                                        # and have key_sets discarded if they contain it
                                        {'program': Program.objects.get(anchor=resource.event.anchor),
                                            'self': resource.user})
    # Should depend on Event as well... IDs are safe, but not necessarily stored objects (seems a common occurence...)
    # though Event shouldn't change much

    def clearAvailableTimes(self, program):
        """ Clear all resources indicating this teacher's availability for a program """
        from esp.resources.models import Resource

        Resource.objects.filter(user=self, event__anchor=program.anchor).delete()

    def addAvailableTime(self, program, timeslot):
        from esp.resources.models import Resource, ResourceType

        # if program.anchor is not timeslot.anchor:
        #    BADNESS

        r = Resource()
        r.user = self
        r.event = timeslot
        r.name = 'Teacher Availability, %s at %s' % (self.name(), timeslot.short_description)
        r.res_type = ResourceType.get_or_create('Teacher Availability')
        r.save()

    def getApplication(self, program, create=True):
        from esp.program.models.app_ import StudentApplication
        
        apps = StudentApplication.objects.filter(user=self, program=program)
        print 'Count: %d' % apps.count()
        if apps.count() > 1:
            raise ESPError(True), '%d applications found for user %s in %s' % (apps.count(), self.username, program.niceName())
        elif apps.count() == 0:
            if create:
                app = StudentApplication(user=self, program=program)
                app.save()
                return app
            else:
                return None
        else:
            return apps[0]

    def getApplication(self, program, create=True):
        from esp.program.models.app_ import StudentApplication
        
        apps = StudentApplication.objects.filter(user=self, program=program)
        print 'Count: %d' % apps.count()
        if apps.count() > 1:
            raise ESPError(True), '%d applications found for user %s in %s' % (apps.count(), self.username, program.niceName())
        elif apps.count() == 0:
            if create:
                app = StudentApplication(user=self, program=program)
                app.save()
                return app
            else:
                return None
        else:
            return apps[0]

    def getClasses(self, program=None, verbs=None):
        from esp.program.models import ClassSubject
        csl = self.getSections(program, verbs)
        pc_ids = [c.parent_class.id for c in csl]
        return ClassSubject.objects.filter(id__in=pc_ids)
    
    def getAppliedClasses(self, program=None):
        #   If priority registration is enabled, add in more verbs.
        if program:
            scrmi = program.getModuleExtension('StudentClassRegModuleInfo')
            verb_list = scrmi.reg_verbs(uris=True)
        else:
            verb_list = ['/Applied']
            
        return self.getClasses(program, verbs=verb_list)
       
    def getEnrolledClasses(self, program=None, request=None):
        """ A new version of getEnrolledClasses that accepts arbitrary registration
        verbs.  If it's too slow we can implement caching like in previous SVN
        revisions. """
        return self.getClasses(program, verbs=['/Enrolled'])

    def getSections(self, program=None, verbs=None):
        """ Since enrollment is not the only way to tie a student to a ClassSection,
        here's a slightly more general function for finding who belongs where. """
        from esp.program.models import ClassSection
        
        if program:
            qsc_base = program.anchor
        else:
            qsc_base = GetNode('Q')
                
        if not verbs:
            verb_base = GetNode('V/Flags/Registration')
                
            csl = ClassSection.objects.filter(QTree(anchor__below=qsc_base,
                                                    anchor__userbit_qsc__verb__below=verb_base)
                                              & Q( anchor__userbit_qsc__user=self,
                                                   anchor__userbit_qsc__enddate__gte=datetime.now())).distinct()

        else:            
            verb_uris = ('V/Flags/Registration' + verb_str for verb_str in verbs)
            
            csl = ClassSection.objects.filter(QTree(anchor__below=qsc_base)
                                              & Q(anchor__userbit_qsc__enddate__gte=datetime.now()),
                                              Q(anchor__userbit_qsc__user=self,
                                                anchor__userbit_qsc__verb__uri__in=verb_uris)
                                              ).distinct()
            

        return csl

    def getEnrolledSections(self, program=None):
        return self.getSections(program, verbs=['/Enrolled'])

    def getRegistrationPriority(self, timeslots):
        """ Finds the highest available priority level for this user across the supplied timeslots. """
        from esp.program.models import Program, RegistrationProfile
        
        if len(timeslots) < 1:
            return 1
        
        prog = Program.objects.get(anchor=timeslots[0].anchor)
        prereg_sections = RegistrationProfile.getLastForProgram(self, prog).preregistered_classes()
        
        priority_dict = {}
        for t in timeslots:
            priority_dict[t.id] = []
            
        for sec in prereg_sections:
            cv = sec.getRegVerbs(self)
            smt = sec.meeting_times.all()
            for t in smt:
                if t.id in priority_dict:
                    for v in cv:
                        if v.parent.name == 'Priority':
                            priority_dict[t.id].append(int(v.name))
        #   Now priority_dict is a dictionary where the keys are timeslot IDs and the values
        #   are lists of taken priority levels.  Merge those and find the lowest positive
        #   integer not in that list.
        all_priorities = []
        for key in priority_dict:
            all_priorities += priority_dict[key]
            
        priority = 1
        while priority in all_priorities:
            priority += 1

        return priority

    def isEnrolledInClass(self, clsObj, request=None):
        verb_str = 'V/Flags/Registration/Enrolled'
        if request:
            verb = request.get_node(verb_str)
        else:
            verb = GetNode(verb_str)

        return UserBit.UserHasPerms(self, clsObj.anchor, verb)

    def canAdminister(self, nodeObj):
        return UserBit.UserHasPerms(self, nodeObj.anchor, GetNode('V/Administer'))

    def canRegToFullProgram(self, nodeObj):
        return UserBit.UserHasPerms(self, nodeObj.anchor, GetNode('V/Flags/RegAllowed/ProgramFull'))

    def hasFinancialAid(self, anchor):
        from esp.program.models import Program, FinancialAidRequest
        progs = [p['id'] for p in Program.objects.filter(anchor=anchor).values('id')]
        apps = FinancialAidRequest.objects.filter(user=self, program__in=progs)
        for a in apps:
            if a.approved:
                return True
        return False

    def paymentStatus(self, anchor=None):
        """ Returns a tuple of (has_paid, status_str, amount_owed, line_items) to indicate
        the user's payment obligations to ESP:
        -   has_paid: True or False, indicating whether any money is owed to
            the accounts under the specified anchor
        -   status: A string briefly explaining the status of the transactions
        -   amount_owed: A Decimal for the amount they need to pay
        -   line_items: A list of the relevant line items
        """
        from esp.accounting_docs.models import Document
        from esp.accounting_core.models import LineItem, Transaction

        if anchor is None:
            anchor = GetNode('Q/Programs')

        receivable_parent = GetNode('Q/Accounts/Receivable')
        realized_parent = GetNode('Q/Accounts/Realized')

        #   We have to check both complete and incomplete documents belonging to the anchor.
        docs = Document.objects.filter(user=self, anchor__rangestart__gte=anchor.rangestart, anchor__rangeend__lte=anchor.rangeend)

        li_list = []
        for d in docs:
            li_list += list(d.txn.lineitem_set.all())

        amt_charged = 0
        amt_expected = 0
        amt_paid = 0
        #   Compute amount charged by looking at line items posted under the specified anchor.
        #   Compute amount expected by looking at line items posted to Accounts Receivable.
        #   Compute amount paid by looking at line items posted to Accounts Realized.
        #   Exclude duplicate line items.  We may want to remove this soon, but it was
        #   a necessity for HSSP/Spark.   -Michael
        previous_li = []
        for li in li_list:
            li_str = '%.2f,%d' % (li.amount, li.anchor.id)
            if li_str not in previous_li:
                previous_li.append(li_str)
            else:
                continue

            if li.anchor in anchor:
                amt_charged -= li.amount
            if li.anchor in receivable_parent:
                amt_expected += li.amount
            if li.anchor in realized_parent:
                amt_paid += li.amount
        has_paid = False
        status = 'Unknown'
        if amt_charged == 0:
            status = 'No charges'
        elif amt_expected != 0:
            if amt_paid == 0:
                status = 'Pending/Unpaid'
            else:
                status = 'Partially paid'
        elif amt_charged > 0 and amt_paid == 0:
            status = 'Unpaid'
        else:
            status = 'Fully paid'
            has_paid = True
        
        amt_owed = amt_charged - amt_paid
        return (has_paid, status, amt_owed, li_list)

    has_paid = lambda x, y: x.paymentStatus(y)[0]
    payment_status_str = lambda x, y: x.paymentStatus(y)[1]
    amount_owed = lambda x, y: x.paymentStatus(y)[2]
    line_items = lambda x, y: x.paymentStatus(y)[3]

    def isOnsite(self, program = None):
        verb = GetNode('V/Registration/OnSite')
        if program is None:
            return (hasattr(self, 'onsite_local') and self.onsite_local is True) or \
                   UserBit.objects.user_has_verb(self, verb)
        else:
            return (hasattr(self, 'onsite_local') and self.onsite_local is True) or \
                    UserBit.UserHasPerms(self, program.anchor, verb)

    def recoverPassword(self):
        # generate the ticket, send the email.
        from esp.dbmail.models import MessageRequest
        from django.template import loader, Context
        from django.contrib.sites.models import Site

        # get the filter object
        filterobj = PersistentQueryFilter.getFilterFromQ(Q(id = self.id),
                                                         User,
                                                         'User %s' % self.username)

        ticket = PasswordRecoveryTicket.new_ticket(self)

        domainname = Site.objects.get_current().domain

        # create the variable modules
        variable_modules = {'user': self, 'ticket': ticket, 'domainname' : domainname}


        newmsg_request = MessageRequest.createRequest(var_dict   = variable_modules,
                                                      subject    = '[ESP] Your Password Recovery For '+domainname,
                                                      recipients = filterobj,
                                                      sender     = '"MIT Educational Studies Program" <esp@mit.edu>',
                                                      creator    = self,
                                                      msgtext    = loader.find_template_source('email/password_recover')[0])

        newmsg_request.save()



    def isAdministrator(self, anchor_object = None):
        if anchor_object is None:
            return UserBit.objects.user_has_verb(self, GetNode('V/Administer'))
        else:
            if hasattr(anchor_object, 'anchor'):
                anchor = anchor_object.anchor
            else:
                anchor = anchor_object

            return UserBit.UserHasPerms(self, anchor, GetNode('V/Administer'))

    isAdmin = isAdministrator

    def delete(self):
        for x in self.userbit_set.all():
            x.delete()
        super(ESPUser, self).delete()

    @classmethod
    def create_membership_methods(cls):
        """
        Creates the methods such as isTeacher that determins whether
        or not the user is a member of that user class.
        """
        user_classes = ('Teacher','Guardian','Educator','Officer','Student')
        overrides = {'Officer': 'Administrator'}
        for user_class in user_classes:
            method_name = 'is%s' % user_class
            bit_name = 'V/Flags/UserRole/%s' % overrides.get(user_class, user_class)
            property_name = '_userclass_%s' % user_class
            def method_gen(bit_name, property_name):
                def _new_method(user):
                    if not hasattr(user, property_name):
                        setattr(user, property_name, bool(UserBit.UserHasPerms(user, GetNode('Q'),
                                                                          GetNode(bit_name))))
                    return getattr(user, property_name)

                _new_method.__name__ = method_name
                _new_method.__doc__ = "Returns ``True`` if the user is a %s and False otherwise." % user_class

                return _new_method

            setattr(cls, method_name, method_gen(bit_name, property_name))

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
        return len(User.objects.filter(username=username.lower()).values('id')[:1]) > 0

    @staticmethod
    def current_schoolyear():
        now = datetime.now()
        curyear = now.year
        if datetime(curyear, 6, 1) > now:
            schoolyear = curyear
        else:
            schoolyear = curyear + 1
        return schoolyear

    def getGrade(self, program = None):
        if hasattr(self, '_grade'):
            return self._grade
        grade = 0
        if self.isStudent():
            if program is None:
                regProf = self.getLastProfile()
            else:
                from esp.program.models import RegistrationProfile
                regProf = RegistrationProfile.getLastForProgram(self,program)
            if regProf and regProf.student_info:
                if regProf.student_info.graduation_year:
                    grade =  ESPUser.gradeFromYOG(regProf.student_info.graduation_year)

        self._grade = grade

        return grade

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


ESPUser.create_membership_methods()

ESPUser._meta.pk.name = "id"
ESPUser._meta.pk.attname = "id"
ESPUser._meta.local_fields[0].column = "id"


shirt_sizes = ('S', 'M', 'L', 'XL', 'XXL')
shirt_sizes = tuple([('14/16', '14/16 (XS)')] + zip(shirt_sizes, shirt_sizes))
shirt_types = (('M', 'Plain'), ('F', 'Fitted (for women)'))

class StudentInfo(models.Model):
    """ ESP Student-specific contact information """
    user = AjaxForeignKey(User, blank=True, null=True)
    graduation_year = models.PositiveIntegerField(blank=True, null=True)
    school = models.CharField(max_length=256,blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    studentrep = models.BooleanField(blank=True, default = False)
    studentrep_expl = models.TextField(blank=True, null=True)
    heardofesp = models.TextField(blank=True, null=True)
# removing shirt information, because this confused people.
#    shirt_size = models.CharField(max_length=5, blank=True, choices=shirt_sizes, null=True)
#    shirt_type = models.CharField(max_length=20, blank=True, choices=shirt_types, null=True)


    def save(self, *args, **kwargs):
        super(StudentInfo, self).save(*args, **kwargs)
        from esp.mailman import add_list_member
        add_list_member('students', self.user)
        add_list_member('announcements', self.user)

    class Meta:
        app_label = 'users'
        db_table = 'users_studentinfo'

    @classmethod
    def ajax_autocomplete(cls, data):
        names = data.strip().split(',')
        last = names[0]

        query_set = cls.objects.filter(user__last_name__istartswith = last.strip())

        if len(names) > 1:
            first  = ','.join(names[1:])
            if len(first.strip()) > 0:
                query_set = query_set.filter(user__first_name__istartswith = first.strip())

        query_set = query_set[:10]

        values = query_set.values('user', 'school', 'graduation_year', 'id')
        #   values = query_set.order_by('user__last_name','user__first_name','id').values('user', 'school', 'graduation_year', 'id')

        for value in values:
            value['user'] = User.objects.get(id=value['user'])
            value['ajax_str'] = '%s - %s %d' % (ESPUser(value['user']).ajax_str(), value['school'], value['graduation_year'])
        return values

    def ajax_str(self):
        return "%s - %s %d" % (ESPUser(self.user).ajax_str(), self.school, self.graduation_year)

    def updateForm(self, form_dict):
        STUDREP_VERB = GetNode('V/Flags/UserRole/StudentRepRequest')
        STUDREP_QSC  = GetNode('Q')
        form_dict['graduation_year'] = self.graduation_year
        form_dict['school']          = self.school
        form_dict['dob']             = self.dob
#        form_dict['shirt_size']      = self.shirt_size
#        form_dict['shirt_type']      = self.shirt_type
        form_dict['heardofesp']      = self.heardofesp
        form_dict['studentrep_expl'] = self.studentrep_expl
        form_dict['studentrep']      = UserBit.UserHasPerms(user = self.user,
                                                            qsc  = STUDREP_QSC,
                                                            verb = STUDREP_VERB)
        return form_dict

    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a StudentInfo record """
        STUDREP_VERB = GetNode('V/Flags/UserRole/StudentRepRequest')
        STUDREP_QSC  = GetNode('Q')

        if regProfile.student_info is None:
            studentInfo = StudentInfo()
            studentInfo.user = curUser
        else:
            studentInfo = regProfile.student_info

        studentInfo.graduation_year = new_data['graduation_year']
        studentInfo.school          = new_data['school']
        studentInfo.dob             = new_data['dob']
        studentInfo.heardofesp      = new_data['heardofesp']
#        studentInfo.shirt_size      = new_data['shirt_size']
#        studentInfo.shirt_type      = new_data['shirt_type']
        studentInfo.studentrep_expl = new_data['studentrep_expl']
        studentInfo.save()
        if new_data['studentrep']:
            #   E-mail membership notifying them of the student rep request.
            subj = '[ESP Membership] Student Rep Request: ' + curUser.first_name + ' ' + curUser.last_name
            to_email = ['esp-membership@mit.edu']
            from_email = 'ESP Profile Editor <regprofile@esp.mit.edu>'
            t = loader.get_template('email/studentreprequest')
            msgtext = t.render(Context({'user': curUser, 'info': studentInfo, 'prog': regProfile.program}))
            send_mail(subj, msgtext, from_email, to_email, fail_silently = True)

            #   Add the user bit representing a student rep request.
            #   The membership coordinator has to make the 'real' student rep bit.
            UserBit.objects.get_or_create(user = curUser,
                                          verb = STUDREP_VERB,
                                          qsc  = STUDREP_QSC,
                                          recursive = False)
        else:
            UserBit.objects.filter(user = curUser,
                                   verb = STUDREP_VERB,
                                   qsc  = STUDREP_QSC).delete()
        return studentInfo

    def __unicode__(self):
        username = "N/A"
        if self.user != None:
            username = self.user.username
        return 'ESP Student Info (%s) -- %s' % (username, str(self.school))

    class Admin:
        search_fields = ['user__first_name','user__last_name','user__username']

class TeacherInfo(models.Model):
    """ ESP Teacher-specific contact information """
    user = AjaxForeignKey(User, blank=True, null=True)
    graduation_year = models.PositiveIntegerField(blank=True, null=True)
    college = models.CharField(max_length=128,blank=True, null=True)
    major = models.CharField(max_length=32,blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    shirt_size = models.CharField(max_length=5, blank=True, choices=shirt_sizes, null=True)
    shirt_type = models.CharField(max_length=20, blank=True, choices=shirt_types, null=True)

    def save(self, *args, **kwargs):
        super(TeacherInfo, self).save(*args, **kwargs)
        from esp.mailman import add_list_member
        add_list_member('teachers', self.user)
        

    class Meta:
        app_label = 'users'
        db_table = 'users_teacherinfo'

    @classmethod
    def ajax_autocomplete(cls, data):
        names = data.strip().split(',')
        last = names[0]

        query_set = cls.objects.filter(user__last_name__istartswith = last.strip())

        if len(names) > 1:
            first  = ','.join(names[1:])
            if len(first.strip()) > 0:
                query_set = query_set.filter(user__first_name__istartswith = first.strip())

        query_set = query_set[:10]
        values = query_set.values('user', 'college', 'graduation_year', 'id')
        #   values = query_set.order_by('user__last_name','user__first_name','id').values('user', 'college', 'graduation_year', 'id')

        for value in values:
            value['user'] = User.objects.get(id=value['user'])
            value['ajax_str'] = '%s - %s %d' % (ESPUser(value['user']).ajax_str(), value['college'], value['graduation_year'])
        return values

    def ajax_str(self):
        return "%s - %s %d" % (ESPUser(self.user).ajax_str(), self.college, self.graduation_year)

    def updateForm(self, form_dict):
        form_dict['graduation_year'] = self.graduation_year
        form_dict['school']          = self.college
        form_dict['major']           = self.major
        form_dict['shirt_size']      = self.shirt_size
        form_dict['shirt_type']      = self.shirt_type
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
        teacherInfo.shirt_size      = new_data['shirt_size']
        teacherInfo.shirt_type      = new_data['shirt_type']
        teacherInfo.save()
        return teacherInfo

    def __unicode__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Teacher Info (%s)' % username

    class Admin:
        search_fields = ['user__first_name','user__last_name','user__username']

class GuardianInfo(models.Model):
    """ ES Guardian-specific contact information """
    user = AjaxForeignKey(User, blank=True, null=True)
    year_finished = models.PositiveIntegerField(blank=True, null=True)
    num_kids = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        app_label = 'users'
        db_table = 'users_guardianinfo'

    def save(self, *args, **kwargs):
        super(GuardianInfo, self).save(*args, **kwargs)
        from esp.mailman import add_list_member
        add_list_member('announcements', self.user)

    @classmethod
    def ajax_autocomplete(cls, data):
        names = data.strip().split(',')
        last = names[0]

        query_set = cls.objects.filter(user__last_name__istartswith = last.strip())

        if len(names) > 1:
            first  = ','.join(names[1:])
            if len(first.strip()) > 0:
                query_set = query_set.filter(user__first_name__istartswith = first.strip())
        query_set = query_set[:10]
        values = query_set.values('user', 'year_finished', 'num_kids', 'id')
        #   values = query_set.order_by('user__last_name','user__first_name','id').values('user', 'year_finished', 'num_kids', 'id')

        for value in values:
            value['user'] = User.objects.get(id=value['user'])
            value['ajax_str'] = '%s - %s %d' % (ESPUser(value['user']).ajax_str(), value['year_finished'], value['num_kids'])
        return values

    def ajax_str(self):
        return "%s - %s %d" % (ESPUser(self.user).ajax_str(), self.year_finished, self.num_kids)

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

    def __unicode__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Guardian Info (%s)' % username

    class Admin:
        search_fields = ['user__first_name','user__last_name','user__username']


class EducatorInfo(models.Model):
    """ ESP Educator-specific contact information """
    user = AjaxForeignKey(User, blank=True, null=True)
    subject_taught = models.CharField(max_length=64,blank=True, null=True)
    grades_taught = models.CharField(max_length=16,blank=True, null=True)
    school = models.CharField(max_length=128,blank=True, null=True)
    position = models.CharField(max_length=64,blank=True, null=True)

    class Meta:
        app_label = 'users'
        db_table = 'users_educatorinfo'

    def save(self, *args, **kwargs):
        super(EducatorInfo, self).save(*args, **kwargs)
        from esp.mailman import add_list_member
        add_list_member('announcements', self.user)

    @classmethod
    def ajax_autocomplete(cls, data):
        names = data.strip().split(',')
        last = names[0]

        query_set = cls.objects.filter(user__last_name__istartswith = last.strip())

        if len(names) > 1:
            first  = ','.join(names[1:])
            if len(first.strip()) > 0:
                query_set = query_set.filter(user__first_name__istartswith = first.strip())
        query_set = query_set[:10]
        values = query_set.values('user', 'position', 'school', 'id')
        #   values = query_set.order_by('user__last_name','user__first_name','id').values('user', 'position', 'school', 'id')

        for value in values:
            value['user'] = User.objects.get(id=value['user'])
            value['ajax_str'] = '%s - %s %d' % (ESPUser(value['user']).ajax_str(), value['position'], value['school'])
        return values

    def ajax_str(self):
        return "%s - %s at %s" % (ESPUser(self.user).ajax_str(), self.position, self.school)

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

    def __unicode__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Educator Info (%s)' % username

    class Admin:
        search_fields = ['user__first_name','user__last_name','user__username']

class ZipCode(models.Model):
    """ Zip Code information """
    zip_code = models.CharField(max_length=5)
    latitude = models.DecimalField(max_digits=10, decimal_places = 6)
    longitude = models.DecimalField(max_digits=10, decimal_places = 6)

    class Meta:
        app_label = 'users'
        db_table = 'users_zipcode'

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
        from decimal import Decimal
        try:
            distance = Decimal(str(distance))
        except:
            raise ESPError(), '%s should be a valid decimal number!' % distance

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

    def __unicode__(self):
        return '%s (%s, %s)' % (self.zip_code,
                                self.longitude,
                                self.latitude)



class ZipCodeSearches(models.Model):
    zip_code = models.ForeignKey(ZipCode)
    distance = models.DecimalField(max_digits = 15, decimal_places = 3)
    zipcodes = models.TextField()

    class Meta:
        app_label = 'users'
        db_table = 'users_zipcodesearches'

    def __unicode__(self):
        return '%s Zip Codes that are less than %s miles from %s' % \
               (len(self.zipcodes.split(',')), self.distance, self.zip_code)

class ContactInfo(models.Model):
    """ ESP-specific contact information for (possibly) a specific user """
    user = AjaxForeignKey(User, blank=True, null=True)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    e_mail = models.EmailField('E-mail address', blank=True, null=True)
    phone_day = PhoneNumberField('Home phone',blank=True, null=True)
    phone_cell = PhoneNumberField('Cell phone',blank=True, null=True)
    phone_even = PhoneNumberField('Alternate phone',blank=True, null=True)
    address_street = models.CharField('Street address',max_length=100,blank=True, null=True)
    address_city = models.CharField('City',max_length=50,blank=True, null=True)
    address_state = USStateField('State',blank=True, null=True)
    address_zip = models.CharField('Zip code',max_length=5,blank=True, null=True)
    address_postal = models.TextField(blank=True,null=True)
    undeliverable = models.BooleanField(default=False)

    class Meta:
        app_label = 'users'
        db_table = 'users_contactinfo'

    def address(self):
        return '%s, %s, %s %s' % \
            (self.address_street,
             self.address_city,
             self.address_state,
             self.address_zip)

    def items(self):
        return self.__dict__.items()

    @classmethod
    def ajax_autocomplete(cls, data):
        names = data.strip().split(',')
        last = names[0]
        query_set = cls.objects.filter(last_name__istartswith = last.strip())
        if len(names) > 1:
            first  = ','.join(names[1:])
            if len(first.strip()) > 0:
                query_set = query_set.filter(first_name__istartswith = first.strip())
        values = query_set.order_by('last_name','first_name','id').values('first_name', 'last_name', 'e_mail', 'id')
        for value in values:
            value['ajax_str'] = '%s, %s (%s)' % (value['last_name'], value['first_name'], value['e_mail'])
        return values

        def ajax_str(self):
            return "%s, %s (%s)" % (self.last_name, self.first_name, self.e_mail)

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
                form_data[prepend+key] = val
        return form_data

    def save(self, *args, **kwargs):
        if self.id != None:
            try:
                old_self = ContactInfo.objects.get(id = self.id)
                if old_self.address_zip != self.address_zip or \
                        old_self.address_street != self.address_street or \
                        old_self.address_city != self.address_city or \
                        old_self.address_state != self.address_state:
                    self.address_postal = None
                    self.undeliverable = False
            except:
                pass
        if self.address_postal != None:
            self.address_postal = str(self.address_postal)

        super(ContactInfo, self).save(*args, **kwargs)

    def __unicode__(self):
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
        search_fields = ['first_name','last_name','user__username']


class K12School(models.Model):
    """
    All the schools that we know about.
    """
    contact = AjaxForeignKey(ContactInfo, null=True,blank=True)
    school_type = models.TextField(blank=True,null=True)
    grades      = models.TextField(blank=True,null=True)
    school_id   = models.CharField(max_length=128,blank=True,null=True)
    contact_title = models.TextField(blank=True,null=True)
    name          = models.TextField(blank=True,null=True)

    class Meta:
        app_label = 'users'
        db_table = 'users_k12school'

    def __unicode__(self):
        if self.contact_id:
            return '"%s" in %s, %s' % (self.name, self.contact.address_city,
                                       self.contact.address_state)
        else:
            return '"%s"' % self.name

    class Admin:
        pass


def GetNodeOrNoBits(nodename, user = AnonymousUser(), verb = None, create=True):
    """ Get the specified node.  Create it only if the specified user has create bits on it """

    DEFAULT_VERB = 'V/Administer/Edit'

    # get a node, if it exists, return it.
    try:
        node = DataTree.get_by_uri(nodename)
        return node
    except:
        pass


    # if we weren't given a verb, use the default one
    if verb == None:
        verb = GetNode(DEFAULT_VERB)

    # get the lowest parent that exists
    lowest_parent = get_lowest_parent(nodename)

    if UserBit.UserHasPerms(user, lowest_parent, verb, recursive_required = True):
        if create:
            # we can now create it
            return GetNode(nodename)
        else:
            raise DataTree.NoSuchNodeException(lowest_parent, nodename)
    else:
        # person not allowed to
        raise PermissionDenied


class PersistentQueryFilter(models.Model):
    """ This class stores generic query filters persistently in the database, for retrieval (by ID, presumably) and
        to pass the query along to multiple pages and retrival (et al). """
    item_model   = models.CharField(max_length=256)            # A string representing the model, for instance User or Program
    q_filter     = models.TextField()                         # A string representing a query filter
    sha1_hash    = models.CharField(max_length=256)            # A sha1 hash of the string representing the query filter
    create_ts    = models.DateTimeField(auto_now_add = True)  # The create timestamp
    useful_name  = models.CharField(max_length=1024, blank=True, null=True) # A nice name to apply to this filter.

    class Meta:
        app_label = 'users'
        db_table = 'users_persistentqueryfilter'

    @staticmethod
    def create_from_Q(item_model, q_filter, description = ''):
        """ The main constructor, please call this. """
        import hashlib
        dumped_filter = pickle.dumps(q_filter)
        foo, created = PersistentQueryFilter.objects.get_or_create(item_model = str(item_model),
                                                                   q_filter = dumped_filter,
                                                                   sha1_hash = hashlib.sha1(dumped_filter).hexdigest())
        foo.useful_name = description
        foo.save()
        return foo

    def get_Q(self):
        """ This will return the Q object that was passed into it. """
        try:
            QObj = pickle.loads(str(self.q_filter))
        except:
            raise ESPError(), 'Invalid Q object stored in database.'

        #   Do not include users if they have disabled their account.
        if self.item_model.find('auth.models.User') >= 0:
            QObj = QObj & Q(is_active=True)

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

        import hashlib
        try:
            qobject_string = pickle.dumps(QObject)
        except:
            qobject_string = ''
        try:
            filterObj = PersistentQueryFilter.objects.get(sha1_hash = hashlib.sha1(qobject_string).hexdigest())#    pass
        except:
            filterObj = PersistentQueryFilter.create_from_Q(item_model  = model,
                                                            q_filter    = QObject,
                                                            description = description)
            filterObj.save() # create a new one.

        return filterObj

    def __unicode__(self):
        return str(self.useful_name)


class ESPUser_Profile(models.Model):
    user = AjaxForeignKey(User, unique=True)

    class Meta:
        app_label = 'users'
        db_table = 'users_espuser_profile'

    def prof(self):
        return ESPUser(self.user)

    class Admin:
        pass

    def __unicode__(self):
        return "ESPUser_Profile for user: %s" % str(self.user)

class PasswordRecoveryTicket(models.Model):
    """ A ticket for changing your password. """
    RECOVER_KEY_LEN = 30
    RECOVER_EXPIRE = 2 # number of days before it expires
    SYMBOLS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

    user = models.ForeignKey(User)
    recover_key = models.CharField(max_length=RECOVER_KEY_LEN)
    expire = models.DateTimeField(null=True)

    def __unicode__(self):
        return "Ticket for %s (expires %s): %s" % (self.user, self.expire, self.recover_key)

    @classmethod
    def new_key(cls):
        """ Generates a new random key. """
        import random
        key = "".join([random.choice(cls.SYMBOLS) for x in range(cls.RECOVER_KEY_LEN)])
        return key

    @classmethod
    def new_ticket(cls, user):
        """ Returns a new (saved) ticket for a specified user. """
        from datetime import datetime, timedelta

        ticket = cls()
        ticket.user = user
        ticket.recover_key = cls.new_key()
        ticket.expire = datetime.now() + timedelta(days = cls.RECOVER_EXPIRE)

        ticket.save()
        return ticket

    @property
    def recover_url(self):
        """ The URL to recover the password. """
        return 'myesp/recoveremail/?code=%s' % self.recover_key

    @property
    def cancel_url(self):
        """ The URL to cancel the ticket. """
        return 'myesp/cancelrecover/?code=%s' % self.recover_key

    def change_password(self, username, password):
        """ If the ticket is valid, saves the password. """
        if not self.is_valid():
            return False
        if self.user.username != username:
            return False

        # Change the password
        self.user.set_password(password)
        self.user.save()

        # Invalidate all other tickets
        self.cancel_all(self.user)
        return True
    change_password.alters_data = True

    def is_valid(self):
        """ Check if the ticket is still valid, kill it if not. """
        from datetime import datetime
        if self.id is not None and datetime.now() < self.expire:
            return True
        else:
            self.cancel()
            return False
    ## technically alters data by calling cancel(), but templates
    ## should be fine with calling this one I guess
    # is_valid.alters_data = True

    def cancel(self):
        """ Cancel a ticket. """
        if self.id is not None:
            self.delete()
    cancel.alters_data = True

    @classmethod
    def cancel_all(cls, user):
        """ Cancel all tickets belong to user. """
        cls.objects.filter(user=user).delete()

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

    def __unicode__(self):
        return self.key




def install():
    """
    Installs some initial useful UserBits.
    This function should be idempotent: if run more than once consecutively,
    subsequent runnings should have no effect on the db.
    """    
        
    # Populate UserBits from the stored list in initial_userbits.py
    from esp.users.initial_userbits import populateInitialUserBits
    populateInitialUserBits()

    if User.objects.count() == 1: # We just did a syncdb;
                                  # the one account is the admin account
        user = User.objects.all()[0]
        AdminUserBits = ( { "user": user,
                            "verb": GetNode("V/Administer"),
                            "qsc": GetNode("Q") },
                          { "user": user,
                            "verb": GetNode("V/Flags/UserRole/Administrator"),
                            "qsc": GetNode("Q"),
                            "recursive": False } )

        populateInitialUserBits(AdminUserBits)

# We can't import these earlier because of circular stuff...
from esp.users.models.userbits import UserBit
from esp.cal.models import Event
from esp.program.models import ClassSubject, ClassSection, Program
from esp.resources.models import Resource
