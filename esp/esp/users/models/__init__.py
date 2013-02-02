__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
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
  Email: web-team@lists.learningu.org
"""

from datetime import datetime, timedelta
from collections import defaultdict

from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.localflavor.us.models import USStateField, PhoneNumberField
from django.contrib.localflavor.us.forms import USStateSelect
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import models
from django.db.models.base import ModelState
from django.db.models.query import Q, QuerySet
from django.http import HttpRequest
from django.template import loader, Context as DjangoContext
from django import forms
from esp.middleware.threadlocalrequest import get_current_request, AutoRequestContext as Context
from django.template.defaultfilters import urlencode

from esp.cal.models import Event
from esp.cache import cache_function, wildcard
from esp.datatree.models import *
from esp.db.fields import AjaxForeignKey
from esp.db.models.prepared import ProcedureManager
from esp.dblog.models import error
from esp.tagdict.models import Tag
from esp.middleware import ESPError
from esp.utils.widgets import NullRadioSelect, NullCheckboxSelect
from django.conf import settings
import simplejson as json
from esp.customforms.linkfields import CustomFormsLinkModel
from esp.customforms.forms import AddressWidget, NameWidget

try:
    import cPickle as pickle
except ImportError:
    import pickle

DEFAULT_USER_TYPES = [
    ['Student', {'label': 'Student (up through 12th grade)', 'profile_form': 'StudentProfileForm'}],
    ['Teacher', {'label': 'Volunteer Teacher', 'profile_form': 'TeacherProfileForm'}],
    ['Guardian', {'label': 'Guardian of Student', 'profile_form': 'GuardianProfileForm'}],
    ['Educator', {'label': 'K-12 Educator', 'profile_form': 'EducatorProfileForm'}],
    ['Volunteer', {'label': 'On-site Volunteer', 'profile_form': 'VolunteerProfileForm'}]
]

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

#   Class to substitute for Django ModelState when necessary
#   (see end of ESPUser.__init__ for usage)
class FakeState(object):
    db = None

class UserAvailability(models.Model):
    user = AjaxForeignKey('ESPUser')
    event = models.ForeignKey(Event)
    role = AjaxForeignKey(DataTree)
    priority = models.DecimalField(max_digits=3, decimal_places=2, default='1.0')

    class Meta:
        db_table = 'users_useravailability'

    def __unicode__(self):
        return u'%s available as %s at %s' % (self.user.username, self.role.name, unicode(self.event))

    def save(self, *args, **kwargs):
        #   Assign default role if not set.
        #   Careful with this; the result may differ for users with multiple types.
        #   (With this alphabetical ordering, you get roles in the order: teacher, student, guardian, educator, administrator)
        if (not hasattr(self, 'role')) or self.role is None:
            queryset = self.user.userbit_set.filter(QTree(verb__below=GetNode('V/Flags/UserRole'))).order_by('-verb__name')
            if queryset.count() > 0:
                self.role = queryset[0].verb
        return super(UserAvailability, self).save(*args, **kwargs)


class ESPUserManager(ProcedureManager):
    pass

def get_studentreg_model():
    from esp.program.models import StudentRegistration
    return StudentRegistration

class ESPUser(User, AnonymousUser):
    """ Create a user of the ESP Website
    This user extends the auth.User of django"""

    class Meta:
        proxy = True
        verbose_name = 'ESP User'
        
    objects = ESPUserManager()
    # this will allow a casting from User to ESPUser:
    #      foo = ESPUser(bar)   <-- foo is now an ``ESPUser''
    def __init__(self, userObj=None, *args, **kwargs):
        # Set up the storage for instance state
        self._state = ModelState()
    
        if isinstance(userObj, ESPUser):
            self.__olduser = userObj.getOld()
            self.__dict__.update(self.__olduser.__dict__)
            self._is_anonymous = userObj.is_anonymous()

        elif isinstance(userObj, (User, AnonymousUser)):
            self.__dict__ = userObj.__dict__
            self.__olduser = userObj
            self._is_anonymous = userObj.is_anonymous()

        elif userObj is not None or len(args) > 0:
            # Initializing a model using non-keyworded args is a horrible idea.
            # No clue why you'd do it, but I won't stop you. -ageng 2009-05-10
            User.__init__(self, userObj, *args, **kwargs)
            self._is_anonymous = False
        else:
            User.__init__(self, *args, **kwargs)
            self._is_anonymous = False

        if not hasattr(self, "_state"):
            ## Django doesn't properly insert this field on proxy models, apparently?
            ## So, fake it. -- aseering 6/28/2010
            self._state = FakeState()

        self.other_user = False

    def is_anonymous(self):
        return self._is_anonymous

    @staticmethod
    def onsite_user():
        if ESPUser.objects.filter(username='onsite').exists():
            return ESPUser.objects.get(username='onsite')
        else:
            return None

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
    def getEditable_ids(self, objType, qsc=None):
        # As far as I know, fbap's cache is still screwy, so we'll retain this cache at a higher level for now --davidben, 2009-04-06
        return UserBit.find_by_anchor_perms(objType, self, GetNode('V/Administer/Edit'), qsc).values_list('id', flat=True)
    getEditable_ids.get_or_create_token(('self',)) # Currently very difficult to determine type, given anchor
    getEditable_ids.depend_on_row(lambda:UserBit, lambda bit: {} if bit.user_id is None else {'self': bit.user},
                                                  lambda bit: bit.applies_to_verb('V/Administer/Edit'))

    def getEditable(self, objType, qsc=None):
        return objType.objects.filter(id__in=self.getEditable_ids(objType, qsc))

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
                      'olduser_name': self.name(),
                      'retUrl'  : retUrl,
                      'retTitle': retTitle,
                      'onsite'  : onsite}

        if user.isAdministrator():
            # Disallow morphing into Administrators.
            # It's too broken, from a security perspective.
            # -- aseering 1/29/2010
            raise ESPError(False), "User '%s' is an administrator; morphing into administrators is not permitted." % user.username

        logout(request)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        request.session['user_morph'] = user_morph

    def is_morphed(self, request=None):
        if not request:
            request = get_current_request()
        return 'user_morph' in request.session

    def get_old(self, request):
        if not self.is_morphed(request):
            return False
        return ESPUser.objects.get(id=request.session['user_morph']['olduser_id'])

    def switch_back(self, request):
        if not 'user_morph' in request.session:
            raise ESPError(), 'Error: You were not another user to begin with!'

        retUrl   = request.session['user_morph']['retUrl']
        new_user = self.get_old(request)

        if not new_user:
            return retUrl

        del request.session['user_morph']
        logout(request)

        old_user = new_user
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
        elif key == 'recover_url':
            return 'http://%s/myesp/recoveremail/?code=%s' % \
                         (settings.DEFAULT_HOST, otheruser.password)
        elif key == 'recover_query':
            return "?code=%s" % otheruser.password
        return ''

    def getTaughtPrograms(self,):
        taught_programs = Program.objects.filter(
            anchor__child_set__child_set__userbit_qsc__user=self,
            anchor__child_set__child_set__userbit_qsc__verb=GetNode('V/Flags/Registration/Teacher'),
            anchor__child_set__child_set__userbit_qsc__qsc__classsubject__status=10)
        taught_programs = taught_programs.distinct()
        return taught_programs

    def getTaughtClasses(self, program = None):
        """ Return all the taught classes for this user. If program is specified, return all the classes under
            that class. For most users this will return an empty queryset. """
        if program is None:
            return self.getTaughtClassesAll()
        else:
            return self.getTaughtClassesFromProgram(program)

    @cache_function
    def getTaughtClassesFromProgram(self, program):
        from esp.program.models import ClassSubject, Program # Need the Class object.
        
        #   Why is it that we had a find_by_anchor_perms function again?
        tr_node = GetNode('V/Flags/Registration/Teacher')
        when = datetime.now()
        all_classes = ClassSubject.objects.filter(
            anchor__userbit_qsc__verb__id=tr_node.id,
            anchor__userbit_qsc__user=self,
            anchor__userbit_qsc__startdate__lte=when,
            anchor__userbit_qsc__enddate__gte=when,
        ).distinct()

        if type(program) != Program: # if we did not receive a program
            error("Expects a real Program object. Not a `"+str(type(program))+"' object.")
        else:
            return all_classes.filter(parent_program = program)
    getTaughtClassesFromProgram.depend_on_row(lambda:UserBit, lambda bit: {'self': bit.user, 'program': Program.objects.get(anchor=bit.qsc.parent.parent)},
                                                              lambda bit: bit.verb_id == GetNode('V/Flags/Registration/Teacher').id and
                                                                          bit.qsc.parent.name == 'Classes' and
                                                                          bit.qsc.parent.parent.program_set.count() > 0 )
    getTaughtClassesFromProgram.depend_on_row(lambda:ClassSubject, lambda cls: {'program': cls.parent_program}) # TODO: auto-row-thing...

    @cache_function
    def getTaughtClassesAll(self):
        from esp.program.models import ClassSubject # Need the Class object.
        
        #   Why is it that we had a find_by_anchor_perms function again?
        tr_node = GetNode('V/Flags/Registration/Teacher')
        when = datetime.now()
        return ClassSubject.objects.filter(
            anchor__userbit_qsc__verb__id=tr_node.id,
            anchor__userbit_qsc__user=self,
            anchor__userbit_qsc__startdate__lte=when,
            anchor__userbit_qsc__enddate__gte=when,
        ).distinct()
    getTaughtClassesAll.depend_on_row(lambda:UserBit, lambda bit: {'self': bit.user},
                                                      lambda bit: bit.verb_id == GetNode('V/Flags/Registration/Teacher').id and
                                                                  bit.qsc.parent.name == 'Classes' and
                                                                  bit.qsc.parent.parent.program_set.count() > 0 )
    getTaughtClassesAll.depend_on_model(lambda:ClassSubject) # should filter by teachers... eh.

    @cache_function
    def getFullClasses_pretty(self, program):
        full_classes = [cls for cls in self.getTaughtClassesFromProgram(program) if cls.is_nearly_full()]
        return "\n".join([cls.emailcode()+": "+cls.title() for cls in full_classes])
    getFullClasses_pretty.depend_on_row(lambda:UserBit, lambda bit: {'self': bit.user},
                                                      lambda bit: bit.verb_id == GetNode('V/Flags/Registration/Teacher').id and
                                                                  bit.qsc.parent.name == 'Classes' and
                                                                  bit.qsc.parent.parent.program_set.count() > 0 )
    getFullClasses_pretty.depend_on_model(lambda:ClassSubject) # should filter by teachers... eh.


    def getTaughtSections(self, program = None):
        if program is None:
            return self.getTaughtSectionsAll()
        else:
            return self.getTaughtSectionsFromProgram(program)

    @cache_function
    def getTaughtSectionsAll(self):
        from esp.program.models import ClassSection
        classes = list(self.getTaughtClassesAll())
        return ClassSection.objects.filter(parent_class__in=classes)
    getTaughtSectionsAll.depend_on_model(lambda:ClassSection)
    getTaughtSectionsAll.depend_on_cache(getTaughtClassesAll, lambda self=wildcard, **kwargs:
                                                              {'self':self})
    @cache_function
    def getTaughtSectionsFromProgram(self, program):
        from esp.program.models import ClassSection
        classes = list(self.getTaughtClasses(program))
        return ClassSection.objects.filter(parent_class__in=classes)
    getTaughtSectionsFromProgram.get_or_create_token(('program',))
    getTaughtSectionsFromProgram.depend_on_row(lambda:ClassSection, lambda instance: {'program': instance.parent_program})
    getTaughtSectionsFromProgram.depend_on_cache(getTaughtClassesFromProgram, lambda self=wildcard, program=wildcard, **kwargs:
                                                                              {'self':self, 'program':program})

    def getTaughtTime(self, program = None, include_scheduled = True, round_to = 0.0):
        """ Return the time taught as a timedelta. If a program is specified, return the time taught for that program.
            If include_scheduled is given as False, we don't count time for already-scheduled classes.
            Rounds to the nearest round_to (if zero, doesn't round at all). """
        user_sections = self.getTaughtSections(program)
        total_time = timedelta()
        round_to = float( round_to )
        if round_to:
            rounded_hours = lambda x: round_to * round( float( x ) / round_to )
        else:
            rounded_hours = lambda x: float( x )
        for s in user_sections:
            if include_scheduled or (s.start_time() is None):
                total_time = total_time + timedelta(hours=rounded_hours(s.duration))
        return total_time

    @staticmethod
    def getUserFromNum(first, last, num):
        if num == '':
            num = 0
        try:
            num = int(num)
        except:
            raise ESPError(), 'Could not find user "%s %s"' % (first, last)
        users = ESPUser.objects.filter(last_name__iexact = last,
                                    first_name__iexact = first).order_by('id')
        if len(users) <= num:
            raise ESPError(False), '"%s %s": Unknown User' % (first, last)
        return users[num]

    @staticmethod
    def getTypes():
        """ Get a list of the different roles an ESP user can have. By default there are four rols,
            but there can be more. (Returns ['Student','Teacher','Educator','Guardian']. """

        return ['Student','Teacher','Educator','Guardian','Volunteer']

    @staticmethod
    def getAllOfType(strType, QObject = True):
        types = ['Student', 'Teacher','Guardian','Educator','Volunteer']

        if strType not in types:
            raise ESPError(), "Invalid type to find all of."

        Q_useroftype      = Q(userbit__verb = GetNode('V/Flags/UserRole/'+strType)) &\
                            Q(userbit__qsc = GetNode('Q'))                          &\
                            UserBit.not_expired('userbit')

        if QObject:
            return Q_useroftype

        else:
            return ESPUser.objects.filter(Q_useroftype)

    @cache_function
    def getAvailableTimes(self, program, ignore_classes=False):
        """ Return a list of the Event objects representing the times that a particular user
            can teach for a particular program. """
        from esp.cal.models import Event

        #   Detect whether the program has the availability module, and assume
        #   the user is always available if it isn't there.
        if program.program_modules.filter(handler='AvailabilityModule').exists():
            valid_events = Event.objects.filter(useravailability__user=self, anchor=program.anchor).order_by('start')
        else:
            valid_events = program.getTimeSlots()

        if not ignore_classes:
            #   Subtract out the times that they are already teaching.
            other_sections = self.getTaughtSections(program)

            other_times = [sec.meeting_times.values_list('id', flat=True) for sec in other_sections]
            for lst in other_times:
                valid_events = valid_events.exclude(id__in=lst)

        return list(valid_events)
    getAvailableTimes.get_or_create_token(('self', 'program',))
    getAvailableTimes.depend_on_cache(getTaughtSectionsFromProgram,
            lambda self=wildcard, program=wildcard, **kwargs:
                 {'self':self, 'program':program, 'ignore_classes':True})
    # FIXME: Really should take into account section's teachers...
    # even though that shouldn't change often
    getAvailableTimes.depend_on_m2m(lambda:ClassSection, 'meeting_times', lambda sec, event: {'program': sec.parent_program})
    getAvailableTimes.depend_on_m2m(lambda:Program, 'program_modules', lambda prog, pm: {'program': prog})
    getAvailableTimes.depend_on_row(lambda:UserAvailability, lambda ua:
                                        # FIXME: What if resource.event.anchor somehow isn't a program?
                                        # Probably want a helper method return a special "nothing" object (XXX: NOT None)
                                        # and have key_sets discarded if they contain it
                                        {'program': Program.objects.get(anchor=ua.event.anchor),
                                            'self': ua.user})
    # Should depend on Event as well... IDs are safe, but not necessarily stored objects (seems a common occurence...)
    # though Event shouldn't change much

    def clearAvailableTimes(self, program):
        """ Clear this teacher's availability for a program """
        self.useravailability_set.filter(QTree(event__anchor__below=program.anchor)).delete()

    def addAvailableTime(self, program, timeslot, role=None):
        from esp.resources.models import Resource, ResourceType
        
        #   Because the timeslot has an anchor, the program is unnecessary.
        #   Default to teacher mode
        if role is None:
            role = GetNode('V/Flags/UserRole/Teacher')
        new_availability, created = UserAvailability.objects.get_or_create(user=self, event=timeslot, role=role)
        new_availability.save()
        
    def convertAvailability(self):
        resources = Resource.objects.filter(user=self)
        for res in resources:
            self.addAvailableTime(Program.objects.all()[0], res.event)
        resources.delete()

    def getApplication(self, program, create=True):
        from esp.program.models.app_ import StudentApplication
        
        apps = list(StudentApplication.objects.filter(user=self, program=program)[:1])
        if len(apps) == 0:
            if create:
                app = StudentApplication(user=self, program=program)
                app.save()
                return app
            else:
                return None
        else:
            return apps[0]

    def listAppResponses(self, program, create=True):
        from esp.program.models.app_ import StudentApplication
        
        apps = StudentApplication.objects.filter(user=self, program=program)
        if apps.count() == 0:
            return []
        else:
            return apps[0].responses.all()

    def getClasses(self, program=None, verbs=None):
        from esp.program.models import ClassSubject
        csl = self.getSections(program, verbs)
        pc_ids = [c.parent_class.id for c in csl]
        return ClassSubject.objects.filter(id__in=pc_ids)
    
    def getAppliedClasses(self, program=None):
        #   If priority registration is enabled, add in more verbs.
        if program:
            scrmi = program.getModuleExtension('StudentClassRegModuleInfo')
            verb_list = [v.name for v in scrmi.reg_verbs()]
        else:
            verb_list = ['Applied']
            
        return self.getClasses(program, verbs=verb_list)

    def getEnrolledClasses(self, program=None, request=None):
        if program is None:
            return self.getEnrolledClassesAll()
        else:
            return self.getEnrolledClassesFromProgram(program)

    def getEnrolledClassesFromProgram(self, program):
        return self.getClasses(program, verbs=['Enrolled'])

    def getEnrolledClassesAll(self):
        return self.getClasses(None, verbs=['Enrolled'])

    def getSections(self, program=None, verbs=None):
        """ Since enrollment is not the only way to tie a student to a ClassSection,
        here's a slightly more general function for finding who belongs where. """
        from esp.program.models import ClassSection, RegistrationType
        
        now = datetime.now()
        
        if verbs:
            rts = RegistrationType.objects.filter(name__in=verbs)
        else:
            rts = RegistrationType.objects.all()

        if program:
            return ClassSection.objects.filter(id__in=self.studentregistration_set.filter(relationship__in=rts, start_date__lte=now, end_date__gte=now).values_list('section', flat=True)).filter(parent_class__parent_program=program)
        else:
            return ClassSection.objects.filter(id__in=self.studentregistration_set.filter(relationship__in=rts, start_date__lte=now, end_date__gte=now).values_list('section', flat=True))

    def getSectionsFromProgram(self, program, verbs=None):
        return self.getSections(program, verbs=verbs)

    def getEnrolledSections(self, program=None):
        if program is None:
            return self.getEnrolledSectionsAll()
        else:
            return self.getEnrolledSectionsFromProgram(program)

    @cache_function
    def getEnrolledSectionsFromProgram(self, program):
        result = list(self.getSections(program, verbs=['Enrolled']))
        for sec in result:
            sec._timeslot_ids = sec.timeslot_ids()
        return result
    def get_sr_model():
        from esp.program.models import StudentRegistration
        return StudentRegistration
    def get_tsid_function():
        from esp.program.models import ClassSection
        return ClassSection.timeslot_ids
    getEnrolledSectionsFromProgram.depend_on_row(get_sr_model, lambda reg: {'self': reg.user})
    getEnrolledSectionsFromProgram.depend_on_cache(get_tsid_function, lambda self=wildcard, **kwargs: {})

    def getEnrolledSectionsAll(self):
        return self.getSections(None, verbs=['Enrolled'])

    @cache_function
    def getFirstClassTime(self, program):
        sections = self.getSections(program, verbs=['Enrolled']).order_by('meeting_times')
        if sections.count() == 0:
            return None
        else:
            if sections[0].meeting_times.count() == 0:
                return None
            else:
                return sections[0].meeting_times.order_by('start')[0]
    getFirstClassTime.depend_on_row(get_sr_model, lambda reg: {'self': reg.user})
    
    def getRegistrationPriority(self, prog, timeslots):
        """ Finds the highest available priority level for this user across the supplied timeslots. 
            Returns 0 if the student is already enrolled in one or more of the timeslots. """
        from esp.program.models import Program, RegistrationProfile
        
        if len(timeslots) < 1:
            return 0
        
        prereg_sections = self.getSectionsFromProgram(prog)
        
        priority_dict = {}
        for t in timeslots:
            priority_dict[t.id] = []
            
        for sec in prereg_sections:
            cv = sec.getRegVerbs(self)
            smt = sec.meeting_times.all()
            for t in smt:
                if t.id in priority_dict:
                    for v in cv:
                        if v.name.startswith('Priority'):
                            try:
                                priority_dict[t.id].append(int(v[9:]))
                            except Exception: # fails if 'Priority' is set, rather than 'Priority/1'
                                priority_dict[t.id].append(1)
                        elif v == 'Enrolled':
                            return 0
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
        
    #   We often request the registration priority for all timeslots individually
    #   because our schedules display enrollment status on a per-timeslot (rather
    #   than per-class) basis.  This function is intended to speed that up.
    def getRegistrationPriorities(self, prog, timeslot_ids):
        num_slots = len(timeslot_ids)
        events = list(Event.objects.filter(id__in=timeslot_ids).order_by('id'))
        result = [0 for i in range(num_slots)]
        id_order = range(num_slots)
        id_order.sort(key=lambda i: timeslot_ids[i])
        for i in range(num_slots):
            result[id_order[i]] = self.getRegistrationPriority(prog, [events[i]])
        return result

    def isEnrolledInClass(self, clsObj, request=None):
        return clsObj.students().filter(id=self.id).exists()

    def canAdminister(self, nodeObj):
        return UserBit.UserHasPerms(self, nodeObj.anchor, GetNode('V/Administer'))

    def canRegToFullProgram(self, nodeObj):
        return UserBit.UserHasPerms(self, nodeObj.anchor, GetNode('V/Flags/RegAllowed/ProgramFull'))

    #   This is needed for cache dependencies on financial aid functions
    def get_finaid_model():
        from esp.program.models import FinancialAidRequest
        return FinancialAidRequest

    @cache_function
    def appliedFinancialAid(self, program):
        return self.financialaidrequest_set.all().filter(program=program, done=True).count() > 0
    #   Invalidate cache when any of the user's financial aid requests are changed
    appliedFinancialAid.depend_on_row(get_finaid_model, lambda fr: {'self': fr.user})

    @cache_function
    def hasFinancialAid(self, anchor):
        from esp.program.models import Program, FinancialAidRequest
        progs = [p['id'] for p in Program.objects.filter(anchor=anchor).values('id')]
        apps = FinancialAidRequest.objects.filter(user=self, program__in=progs)
        for a in apps:
            if a.approved:
                return True
        return False
    hasFinancialAid.depend_on_row(get_finaid_model, lambda fr: {'self': fr.user})

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
            li_str = '%.2f,%d,%d' % (li.amount, li.li_type.id, li.anchor.id)
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
        from django.contrib.sites.models import Site
        from django.conf import settings

        # we have a lot of users with no email (??)
        #  let's at least display a sensible error message
        if self.email.strip() == '':
            raise ESPError(), 'User %s has blank email address; cannot recover password. Please contact webmasters to reset your password.' % self.username

        # email addresses
        to_email = ['%s <%s>' % (self.name(), self.email)]
        from_email = settings.SERVER_EMAIL

        # create the ticket
        ticket = PasswordRecoveryTicket.new_ticket(self)

        # email subject
        domainname = Site.objects.get_current().domain
        subject = '[%s] Your Password Recovery For %s ' % (settings.ORGANIZATION_SHORT_NAME, domainname)

        # generate the email text
        t = loader.get_template('email/password_recover')
        msgtext = t.render(DjangoContext({'user': self,
                                    'ticket': ticket,
                                    'domainname': domainname,
                                    'orgname': settings.ORGANIZATION_SHORT_NAME,
                                    'institution': settings.INSTITUTION_NAME}))

        # Do NOT fail_silently. We want to know if there's a problem.
        send_mail(subject, msgtext, from_email, to_email)


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

    @staticmethod
    def getAllUserTypes():
        tag_data = Tag.getTag('user_types')
        result = DEFAULT_USER_TYPES
        result_labels = [x[0] for x in result]
        if tag_data:
            json_data = json.loads(tag_data)
            for entry in json_data:
                if entry[0] not in result_labels:
                    result.append(entry)
                else:
                    result[result_labels.index(entry[0])][1] = entry[1]
        return result

    def getUserTypes(self):
        """ Return the set of types for this user """
        retVal = UserBit.valid_objects().filter(user=self, verb__parent=GetNode("V/Flags/UserRole")).values_list('verb__name', flat=True).distinct()
        if len(retVal) == 0:
            UserBit.objects.create(user=self, verb=GetNode("V/Flags/UserRole/Student"), qsc=GetNode("Q"))
            retVal = UserBit.valid_objects().filter(user=self, verb__parent=GetNode("V/Flags/UserRole")).values_list('verb__name', flat=True).distinct()
            
        return retVal
        
    @classmethod
    def create_membership_methods(cls):
        """
        Creates the methods such as isTeacher that determins whether
        or not the user is a member of that user class.
        """
        user_classes = ('Teacher','Guardian','Educator','Officer','Student','Volunteer')
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

    @classmethod
    def get_unused_username(cls, first_name, last_name):
        username = base_uname = (first_name[0] + last_name).lower()
        if cls.objects.filter(username = username).count() > 0:
            i = 2
            username = base_uname + str(i)
            while cls.objects.filter(username = username).count() > 0:
                i += 1
                username = base_uname + str(i)
        return username
        
    def makeVolunteer(self):
        ub, created = UserBit.objects.get_or_create(user=self,
                                qsc=GetNode('Q'),
                                verb=GetNode('V/Flags/UserRole/Volunteer'))
        ub.renew()
        
    def canEdit(self, nodeObj):
        """Returns True or False if the user can edit the node object"""
        # Axiak
        return UserBit.UserHasPerms(self, nodeObj.anchor, GetNode('V/Administer/Edit'))

    def getMiniBlogEntries(self):
        """Return all miniblog posts this person has V/Subscribe bits for"""
        # Axiak 12/17
        from esp.miniblog.models import Entry
        return UserBit.find_by_anchor_perms(Entry, self, GetNode('V/Subscribe')).order_by('-timestamp')

    def getVolunteerOffers(self, program):
        return self.volunteeroffer_set.filter(request__program=program)

    @staticmethod
    def isUserNameTaken(username):
        return len(User.objects.filter(username=username.lower()).values('id')[:1]) > 0

    @staticmethod
    def current_schoolyear():
        now = datetime.now()
        curyear = now.year
        # Changed from 6/1 to 5/1 rollover so as not to affect start of Summer HSSP registration
        # - Michael P 5/24/2010
        # Changed from 5/1 to 7/31 rollover to as to neither affect registration starts nor occur prior to graduation.
        # Adam S 8/1/2010
        #if datetime(curyear, 6, 1) > now:
        if datetime(curyear, 7, 31) > now:
            schoolyear = curyear
        else:
            schoolyear = curyear + 1
        return schoolyear

    @cache_function
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
                    if program:
                        grade += program.incrementGrade() # adds 1 if appropriate tag is set; else does nothing
                        

        self._grade = grade

        return grade
    #   The cache will need to be cleared once per academic year.
    getGrade.depend_on_row(lambda: StudentInfo, lambda info: {'self': info.user})
    getGrade.depend_on_row(lambda: Tag, lambda tag: {'program' :  tag.target})

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

shirt_sizes = ('S', 'M', 'L', 'XL', 'XXL')
shirt_sizes = tuple([('14/16', '14/16 (XS)')] + zip(shirt_sizes, shirt_sizes))
shirt_types = (('M', 'Plain'), ('F', 'Fitted (for women)'))
food_choices = ('Anything', 'Vegetarian', 'Vegan')
food_choices = zip(food_choices, food_choices)

class StudentInfo(models.Model):
    """ ESP Student-specific contact information """
    user = AjaxForeignKey(ESPUser, blank=True, null=True)
    graduation_year = models.PositiveIntegerField(blank=True, null=True)
    k12school = AjaxForeignKey('K12School', help_text='Begin to type your school name and select your school if it comes up.', blank=True, null=True)
    school = models.CharField(max_length=256,blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    studentrep = models.BooleanField(blank=True, default = False)
    studentrep_expl = models.TextField(blank=True, null=True)
    heard_about = models.TextField(blank=True, null=True)
    food_preference = models.CharField(max_length=256,blank=True,null=True)
    shirt_size = models.CharField(max_length=5, blank=True, choices=shirt_sizes, null=True)
    shirt_type = models.CharField(max_length=20, blank=True, choices=shirt_types, null=True)

    medical_needs = models.TextField(blank=True, null=True)

    schoolsystem_id = models.CharField(max_length=32, blank=True, null=True)
    schoolsystem_optout = models.BooleanField(default=False)
    post_hs = models.TextField(default='', blank=True)
    transportation = models.TextField(default='', blank=True)

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
        #   Display data from school field in the k12school box if there's no k12school data.
        if self.k12school:
            form_dict['k12school']       = self.k12school_id
        else:
            form_dict['k12school']   = self.school
        form_dict['school']          = self.school
        form_dict['dob']             = self.dob
        if Tag.getTag('studentinfo_shirt_options'):
            form_dict['shirt_size']      = self.shirt_size
            form_dict['shirt_type']      = self.shirt_type
        if Tag.getTag('studentinfo_food_options'):
            form_dict['food_preference'] = self.food_preference
        form_dict['heard_about']      = self.heard_about
        form_dict['studentrep_expl'] = self.studentrep_expl
        form_dict['studentrep']      = UserBit.UserHasPerms(user = self.user,
                                                            qsc  = STUDREP_QSC,
                                                            verb = STUDREP_VERB)
        form_dict['schoolsystem_id'] = self.schoolsystem_id
        form_dict['medical_needs'] = self.medical_needs
        form_dict['schoolsystem_optout'] = self.schoolsystem_optout
        form_dict['post_hs'] = self.post_hs
        form_dict['transportation'] = self.transportation
        return form_dict

    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a StudentInfo record """
        STUDREP_VERB = GetNode('V/Flags/UserRole/StudentRepRequest')
        STUDREP_QSC  = GetNode('Q')

        if regProfile.student_info is None:
            studentInfo = StudentInfo()
        else:
            studentInfo = regProfile.student_info
        if not studentInfo.user:
            studentInfo.user = curUser
        elif studentInfo.user != curUser: # this should never happen, but you never know....
            raise ESPError(), "Your registration profile is corrupted. Please contact esp-web@mit.edu, with your name and username in the message, to correct this issue."

        studentInfo.graduation_year = new_data['graduation_year']
        try:
            if isinstance(new_data['k12school'], K12School):
                studentInfo.k12school = new_data['k12school']
            else:
                if isinstance(new_data['k12school'], int):
                    studentInfo.k12school = K12School.objects.get(id=int(new_data['k12school']))
                else:
                    studentInfo.k12school = K12School.objects.filter(name__icontains=new_data['k12school'])[0]
                    
        except:
            print 'Error, could not find k12school for "%s"' % new_data['k12school']
            studentInfo.k12school = None
            
        studentInfo.school          = new_data['school'] if not studentInfo.k12school else studentInfo.k12school.name
        studentInfo.dob             = new_data['dob']
        
        studentInfo.heard_about      = new_data.get('heard_about', '')

        if 'shirt_size' in new_data and 'shirt_type' in new_data:
            studentInfo.shirt_size      = new_data['shirt_size']
            studentInfo.shirt_type      = new_data['shirt_type']

        if 'food_preference' in new_data:
            studentInfo.food_preference      = new_data['food_preference']

        
        studentInfo.studentrep = new_data.get('studentrep', False)    
        studentInfo.studentrep_expl = new_data.get('studentrep_expl', '')

        studentInfo.schoolsystem_optout = new_data.get('schoolsystem_optout', '')
        studentInfo.schoolsystem_id = new_data.get('schoolsystem_id', '')
        studentInfo.post_hs = new_data.get('post_hs', '')
        studentInfo.medical_needs = new_data.get('medical_needs', '')
        studentInfo.transportation = new_data.get('transportation', '')        
        studentInfo.save()
        if new_data.get('studentrep', False):
            #   E-mail membership notifying them of the student rep request.
            subj = '[%s Membership] Student Rep Request: %s %s' % (settings.ORGANIZATION_SHORT_NAME, curUser.first_name, curUser.last_name)
            to_email = [settings.DEFAULT_EMAIL_ADDRESSES['membership']]
            from_email = 'ESP Profile Editor <regprofile@%s>' % settings.DEFAULT_HOST
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

    def getSchool(self):
        """ Obtain a string representation of the student's school  """ 
        if self.k12school:
            return self.k12school
        elif self.school:
            return self.school
        else:
            return None

    def __unicode__(self):
        username = "N/A"
        if self.user != None:
            username = self.user.username
        return 'ESP Student Info (%s) -- %s' % (username, unicode(self.school))

class TeacherInfo(models.Model, CustomFormsLinkModel):
    """ ESP Teacher-specific contact information """
    
    #customforms definitions
    form_link_name = 'TeacherInfo'
    link_fields_list = [
        ('graduation_year', 'Graduation year'), 
        ('from_here', 'Current student checkbox'), 
        ('is_graduate_student', 'Graduate student status'),
        ('college', 'School/employer'),
        ('major', 'Major/department'),
        ('bio', 'Biography'),
        ('shirt_size', 'Shirt size'),
        ('shirt_type', 'Shirt type'),
        ('full_legal_name', 'Legal name'),
        ('university_email', 'University e-mail address'),
        ('student_id', 'Student ID number'),
        ('mail_reimbursement', 'Reimbursement checkbox'),
    ]
    link_fields_widgets = {
        'from_here': NullRadioSelect, 
        'is_graduate_student': NullCheckboxSelect,
        'mail_reimbursement': forms.CheckboxInput,
    }
    
    user = AjaxForeignKey(User, blank=True, null=True)
    graduation_year = models.CharField(max_length=4, blank=True, null=True)
    from_here = models.NullBooleanField(null=True)
    is_graduate_student = models.NullBooleanField(blank=True, null=True)
    college = models.CharField(max_length=128,blank=True, null=True)
    major = models.CharField(max_length=32,blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    shirt_size = models.CharField(max_length=5, blank=True, choices=shirt_sizes, null=True)
    shirt_type = models.CharField(max_length=20, blank=True, choices=shirt_types, null=True)

    full_legal_name = models.CharField(max_length=128, blank=True, null=True)
    university_email = models.EmailField(blank=True, null=True)
    student_id = models.CharField(max_length=128, blank=True, null=True)
    mail_reimbursement = models.NullBooleanField(blank=True, null=True)

    @classmethod
    def cf_link_instance(cls, request):
        """
        Uses the request object to return the appropriate instance for this model,
        for use by custom-forms.
        It should either return the instance, or 'None', if the corresponding instance doesn't exist.
        """
        queryset=cls.objects.filter(user=request.user).order_by('-id')
        if queryset: return queryset[0] 
        else: return None
        
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
            value['ajax_str'] = u'%s - %s %s' % (ESPUser(value['user']).ajax_str(), value['college'], value['graduation_year'])
        return values

    def ajax_str(self):
        return u'%s - %s %s' % (ESPUser(self.user).ajax_str(), self.college, self.graduation_year)

    def updateForm(self, form_dict):
        form_dict['graduation_year'] = self.graduation_year
        form_dict['from_here']        = self.from_here
        form_dict['is_graduate_student'] = self.is_graduate_student
        form_dict['school']          = self.college
        form_dict['major']           = self.major
        form_dict['shirt_size']      = self.shirt_size
        form_dict['shirt_type']      = self.shirt_type
        if Tag.getTag('teacherinfo_reimbursement_options'):
            form_dict['full_legal_name']    = self.full_legal_name
            form_dict['university_email']   = self.university_email
            form_dict['student_id']         = self.student_id
            form_dict['mail_reimbursement'] = self.mail_reimbursement
        return form_dict

    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a TeacherInfo record """
        new_data = defaultdict(str, new_data) # Don't require all fields to be present
        if regProfile.teacher_info is None:
            teacherInfo = TeacherInfo()
            teacherInfo.user = curUser
        else:
            teacherInfo = regProfile.teacher_info
        teacherInfo.graduation_year = new_data['graduation_year']
        teacherInfo.from_here        = (new_data['from_here'] == "True")
        teacherInfo.is_graduate_student = new_data['is_graduate_student']
        teacherInfo.college         = new_data['school']
        teacherInfo.major           = new_data['major']
        teacherInfo.shirt_size      = new_data['shirt_size']
        teacherInfo.shirt_type      = new_data['shirt_type']
        if Tag.getTag('teacherinfo_reimbursement_options'):
            teacherInfo.full_legal_name    = new_data['full_legal_name']
            teacherInfo.university_email   = new_data['university_email']
            teacherInfo.student_id         = new_data['student_id']
            teacherInfo.mail_reimbursement = new_data['mail_reimbursement']
        teacherInfo.save()
        return teacherInfo

    def __unicode__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Teacher Info (%s)' % username

    class Meta:
        app_label = 'users'


class GuardianInfo(models.Model):
    """ ES Guardian-specific contact information """
    user = AjaxForeignKey(ESPUser, blank=True, null=True)
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


class EducatorInfo(models.Model):
    """ ESP Educator-specific contact information """
    user = AjaxForeignKey(ESPUser, blank=True, null=True)
    subject_taught = models.CharField(max_length=64,blank=True, null=True)
    grades_taught = models.CharField(max_length=16,blank=True, null=True)
    school = models.CharField(max_length=128,blank=True, null=True)
    position = models.CharField(max_length=64,blank=True, null=True)
    k12school = models.ForeignKey('K12School', blank=True, null=True)

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
            value['ajax_str'] = '%s - %s %s' % (ESPUser(value['user']).ajax_str(), value['position'], value['school'])
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
            distance_decimal = Decimal(str(distance))
            distance_float = float(str(distance))
        except:
            raise ESPError(), '%s should be a valid decimal number!' % distance

        if distance < 0:
            distance *= -1

        oldsearches = ZipCodeSearches.objects.filter(zip_code = self,
                                                     distance = distance_decimal)

        if len(oldsearches) > 0:
            return oldsearches[0].zipcodes.split(',')

        all_zips = list(ZipCode.objects.exclude(id = self.id))
        winners  = [ self.zip_code ]

        winners += [ zipc.zip_code for zipc in all_zips
                     if self.distance(zipc) <= distance_float ]

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

class ContactInfo(models.Model, CustomFormsLinkModel):
    """ ESP-specific contact information for (possibly) a specific user """
    
    #customforms definitions
    form_link_name = 'ContactInfo'
    link_fields_list = [
        ('phone_day','Phone number'),
        ('e_mail','E-mail address'),
        ('address', 'Address'),
        ('name', 'Name'),
        ('receive_txt_message', 'Text message request'),
        #   Commented out since it may cause confusion: ('phone_cell', 'Cell phone number')
    ]
    link_fields_widgets = {
        'address_state': USStateSelect,
        'address': AddressWidget,
        'name': NameWidget,
    }
    link_compound_fields = {
        'address': ['address_street', 'address_city', 'address_state', 'address_zip'],
        'name': ['first_name', 'last_name'],
    }

    @classmethod
    def cf_link_instance(cls, request):
        """
        Ues the request object to return the appropriate instance for this model,
        for use by custom-forms.
        It should either return the instance, or 'None', if the corresponding instance doesn't exist.
        """
        queryset=cls.objects.filter(user=request.user).order_by('-id')
        if queryset: return queryset[0] 
        else: return None

    user = AjaxForeignKey(User, blank=True, null=True)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    e_mail = models.EmailField('E-mail address', blank=True, null=True)
    phone_day = PhoneNumberField('Home phone',blank=True, null=True)
    phone_cell = PhoneNumberField('Cell phone',blank=True, null=True)
    receive_txt_message = models.BooleanField(default=False)
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

    def _distance_from(self, zip):
        try:
            myZip = ZipCode.objects.get(zip_code = self.address_zip)
            remoteZip = ZipCode.objects.get(zip_code = zip)
            return myZip.distance(remoteZip)
        except:
            return -1




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
        #   Hack: If the 'no guardian e-mail' Tag is on, check the box for 
        #   "my parent/guardian doesn't have e-mail" if the e-mail field is blank.
        if Tag.getTag('allow_guardian_no_email') and prepend == 'guard_':
            print 'Testing: %s' % self.e_mail
            if not self.e_mail or len(self.e_mail) < 3:
                form_data['guard_no_e_mail'] = True
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

        if self._distance_from("02139") < 50:
            from esp.mailman import add_list_member
            try:
                add_list_member("announcements_local", self.e_mail)
            except:
                pass
            
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


class K12SchoolManager(models.Manager):
    def other(self):
        return self.get_or_create(name='Other')[0]
    def most(self):
        return self.exclude(name='Other').order_by('name')

class K12School(models.Model):
    """
    All the schools that we know about.
    """
    contact = AjaxForeignKey(ContactInfo, null=True,blank=True, 
        help_text='A set of contact information for this school. Type to search by name (Last, First), or <a href="/admin/users/contactinfo/add/">go edit a new one</a>.')
    school_type = models.TextField(blank=True, null=True, 
        help_text='i.e. Public, Private, Charter, Magnet, ...')
    grades      = models.TextField(blank=True, null=True, 
        help_text='i.e. "PK, K, 1, 2, 3"')
    school_id   = models.CharField(max_length=128, blank=True, null=True,
        help_text='An 8-digit ID number.')
    contact_title = models.TextField(blank=True,null=True)
    name          = models.TextField(blank=True,null=True)

    objects = K12SchoolManager()

    class Meta:
        app_label = 'users'
        db_table = 'users_k12school'

    @classmethod
    def ajax_autocomplete(cls, data, allow_non_staff=True):
        name = data.strip()
        query_set = cls.objects.filter(name__icontains = name)
        values = query_set.order_by('name','id').values('name', 'id')
        for value in values:
            value['ajax_str'] = '%s' % (value['name'])
        return values

    def __unicode__(self):
        if self.contact_id:
            return '%s in %s, %s' % (self.name, self.contact.address_city,
                                       self.contact.address_state)
        else:
            return '%s' % self.name

    @classmethod
    def choicelist(cls, other_help_text=''):
        if other_help_text:
            other_help_text = u' (%s)' % other_help_text
        o = cls.objects.other()
        lst = [ ( x.id, x.name ) for x in cls.objects.most() ]
        lst.append( (o.id, o.name + other_help_text) )
        return lst


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
            raise DataTree.NoSuchNodeException(lowest_parent, [nodename])
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
        
        # Deal with multiple instances
        query_q = Q(item_model = str(item_model), q_filter = dumped_filter, sha1_hash = hashlib.sha1(dumped_filter).hexdigest())
        pqfs = PersistentQueryFilter.objects.filter(query_q)
        if pqfs.count() > 0:
            foo = pqfs[0]
        else:
            foo, created = PersistentQueryFilter.objects.get_or_create(item_model = str(item_model),
                                                                   q_filter = dumped_filter,
                                                                   sha1_hash = hashlib.sha1(dumped_filter).hexdigest())
        foo.useful_name = description
        foo.save()
        return foo

    def get_Q(self, restrict_to_active = True):
        """ This will return the Q object that was passed into it. """
        try:
            QObj = pickle.loads(str(self.q_filter))
        except:
            raise ESPError(), 'Invalid Q object stored in database.'

        #   Do not include users if they have disabled their account.
        if restrict_to_active and self.item_model.find('auth.models.User') >= 0:
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
    user = AjaxForeignKey(ESPUser, unique=True)

    class Meta:
        app_label = 'users'
        db_table = 'users_espuser_profile'

    def prof(self):
        return ESPUser(self.user)

    class Admin:
        pass

    def __unicode__(self):
        return "ESPUser_Profile for user: %s" % unicode(self.user)

class PasswordRecoveryTicket(models.Model):
    """ A ticket for changing your password. """
    RECOVER_KEY_LEN = 30
    RECOVER_EXPIRE = 2 # number of days before it expires
    SYMBOLS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

    user = models.ForeignKey(User)
    recover_key = models.CharField(max_length=RECOVER_KEY_LEN)
    expire = models.DateTimeField(null=True)

    class Meta:
        app_label = 'users'

    def __unicode__(self):
        return "Ticket for %s (expires %s): %s" % (self.user, self.expire, self.recover_key)

    @staticmethod
    def new_key():
        """ Generates a new random key. """
        import random
        key = "".join([random.choice(PasswordRecoveryTicket.SYMBOLS) for x in range(PasswordRecoveryTicket.RECOVER_KEY_LEN)])
        return key

    @staticmethod
    def new_ticket(user):
        """ Returns a new (saved) ticket for a specified user. """

        ticket = PasswordRecoveryTicket()
        ticket.user = user
        ticket.recover_key = PasswordRecoveryTicket.new_key()
        ticket.expire = datetime.now() + timedelta(days = PasswordRecoveryTicket.RECOVER_EXPIRE)

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

        # Change the password, and activate the account
        self.user.set_password(password)
        self.user.is_active = True
        self.user.save()

        # Invalidate all other tickets
        self.cancel_all(self.user)
        return True
    change_password.alters_data = True

    def is_valid(self):
        """ Check if the ticket is still valid, kill it if not. """
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
            self.expire = datetime(1990, 8, 3)
            self.delete()
    cancel.alters_data = True

    @staticmethod
    def cancel_all(user):
        """ Cancel all tickets belong to user. """
        PasswordRecoveryTicket.objects.filter(user=user).delete()

class DBList(object):
    """ Useful abstraction for the list of users.
        Not meant for anything but users_get_list...
    """
    totalnum = False # we dont' know how many there are.
    key      = ''
    QObject  = None

    def count(self, override = False):
        """ This is used to count how many objects we are talking about.
            If override is true, it will not retrieve the number from cache
            or from this instance. If it's true, it will try.
        """
        from esp.users.models import User

        cache_id = urlencode('DBListCount: %s' % (self.key))

        retVal   = cache.get(cache_id) # get the cached result
        if self.QObject: # if there is a q object we can just
            if not self.totalnum:
                if override:
                    self.totalnum = ESPUser.objects.filter(self.QObject).distinct().count()
                    cache.set(cache_id, self.totalnum, 60)
                else:
                    cachedval = cache.get(cache_id)
                    if cachedval is None:
                        self.totalnum = ESPUser.objects.filter(self.QObject).distinct().count()
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

class EmailPref(models.Model):
    email = models.EmailField(max_length=64, blank=True, null=True, unique=True)
    email_opt_in = models.BooleanField(default = True)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    sms_number = PhoneNumberField(blank=True, null=True)
    sms_opt_in = models.BooleanField(default = False)
    class Meta:
        app_label = 'users'

def install():
    """
    Installs some initial useful UserBits.
    This function should be idempotent: if run more than once consecutively,
    subsequent runnings should have no effect on the db.
    """    
        
    # Populate UserBits from the stored list in initial_userbits.py
    from esp.users.initial_userbits import populateInitialUserBits
    populateInitialUserBits()

    if ESPUser.objects.count() == 1: # We just did a syncdb;
                                  # the one account is the admin account
        user = ESPUser.objects.all()[0]
        AdminUserBits = ( { "user": user,
                            "verb": GetNode("V/Administer"),
                            "qsc": GetNode("Q") },
                          { "user": user,
                            "verb": GetNode("V/Flags/UserRole/Administrator"),
                            "qsc": GetNode("Q"),
                            "recursive": False } )

        populateInitialUserBits(AdminUserBits)

    #   Ensure that there is an onsite user
    if not ESPUser.onsite_user():
        ESPUser.objects.create(username='onsite', first_name='Onsite', last_name='User')
        print 'Created onsite user, please set their password in the admin interface.'

# We can't import these earlier because of circular stuff...
from esp.users.models.userbits import UserBit
from esp.users.models.forwarder import UserForwarder
from esp.cal.models import Event
from esp.program.models import ClassSubject, ClassSection, Program
from esp.resources.models import Resource

