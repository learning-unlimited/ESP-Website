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
  Email: web-team@learningu.org
"""

from collections import defaultdict
from datetime import datetime, timedelta, date
from pytz import country_names
import json
import logging
logger = logging.getLogger(__name__)
import functools

from django import forms, dispatch
from django.conf import settings
from django.contrib.auth import logout, login, REDIRECT_FIELD_NAME
from django.contrib.auth.models import User, AnonymousUser, Group, UserManager
from localflavor.us.models import PhoneNumberField
from localflavor.us.forms import USStateSelect

from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import signals
from django.db.models.base import ModelState
from django.db.models.manager import Manager
from django.db.models.query import Q
from django.http import HttpResponseRedirect
from django.template import loader
from django.template.defaultfilters import urlencode
from django.template.loader import render_to_string
from django_extensions.db.models import TimeStampedModel
from django.core import urlresolvers
from django.utils.functional import SimpleLazyObject
from django.utils.safestring import mark_safe


from esp.cal.models import Event, EventType
from argcache import cache_function, wildcard
from esp.customforms.linkfields import CustomFormsLinkModel
from esp.customforms.forms import AddressWidget, NameWidget
from esp.db.fields import AjaxForeignKey
from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request, AutoRequestContext as Context
from esp.tagdict.models import Tag
from esp.utils.decorators import enable_with_setting
from esp.utils.expirable_model import ExpirableModel
from esp.utils.widgets import NullRadioSelect, NullCheckboxSelect
from esp.utils.query_utils import nest_Q

from urllib import quote

try:
    import cPickle as pickle
except ImportError:
    import pickle

DEFAULT_USER_TYPES = [
    ['Student', {'label': 'Student (up through 12th grade)', 'profile_form': 'StudentProfileForm'}],
    ['Teacher', {'label': 'Volunteer Teacher', 'profile_form': 'TeacherProfileForm'}],
    ['Guardian', {'label': 'Guardian of Student', 'profile_form': 'GuardianProfileForm'}],
    ['Educator', {'label': 'K-12 Educator', 'profile_form': 'EducatorProfileForm'}],
    ['Volunteer', {'label': 'Onsite Volunteer', 'profile_form': 'VolunteerProfileForm'}]
]

def admin_required(func):
    @functools.wraps(func)
    def wrapped(request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated():
            return HttpResponseRedirect('%s?%s=%s' % (settings.LOGIN_URL, REDIRECT_FIELD_NAME, quote(request.get_full_path())))
        elif not request.user.isAdministrator():
            raise PermissionDenied
        return func(request, *args, **kwargs)
    return wrapped

class UserAvailability(models.Model):
    user = AjaxForeignKey('ESPUser')
    event = models.ForeignKey(Event)
    role = models.ForeignKey('auth.Group')
    priority = models.DecimalField(max_digits=3, decimal_places=2, default='1.0')

    class Meta:
        app_label = 'users'
        db_table = 'users_useravailability'

    def __unicode__(self):
        return u'%s available as %s at %s' % (self.user.username, self.role.name, unicode(self.event))

    def save(self, *args, **kwargs):
        #   Assign default role if not set.
        #   Careful with this; the result may differ for users with multiple types.
        #   (With this alphabetical ordering, you get roles in the order: teacher, student, guardian, educator, administrator)
        if (not hasattr(self, 'role')) or self.role is None:
            self.role = self.user.getUserTypes()[0]
        return super(UserAvailability, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return self.event.program.get_manage_url()+"edit_availability?user="+str(self.user.id)


class ESPUserManager(UserManager):
    pass

class BaseESPUser(object):
    """ Base class for ESPUser and AnonymousESPUser.
    Pretty much anything from ESPUser that isn't directly related
    to being a model should go here. """

    objects = ESPUserManager()
    other_user = False

    def __init__(self, *args, **kwargs):
        # This is last in ESPUser's method resolution order, and
        # AnonymousUser doesn't do anything in its __init__,
        # so there's no need for a super() call unless you're changing
        # inheritance structure of this, ESPUser, or AnonymousESPUser,
        # or if Django has changed something. Adding it anyway in case
        # AnonymousUser changes in the future.
        super(BaseESPUser, self).__init__()
        self.create_membership_methods()

    @classmethod
    def create_membership_methods(cls):
        """
        Setup for the ESPUser membership methods
        """
        if not hasattr(cls, 'isOfficer'):
            for user_type in cls.getTypes(use_tag=False):
                # Make sure that all of the default user types have membership
                # methods defined, because some (such as isStudent()) are used
                # in the code even if that user type isn't included in the Tag
                # override. Start by defining all the membership methods for
                # the default types as returning False, and then overwrite them
                # as necessary.
                setattr(cls, 'is%s' % user_type, lambda user: False)
            for user_type in cls.getTypes() + ['Officer']:
                setattr(cls, 'is%s' % user_type, cls.create_membership_method(user_type))

    @staticmethod
    def grade_options():
        """ Returns a list<int> of valid grades """
        tag_val = Tag.getTag('student_grade_options')
        if tag_val is None:
            return range(7, 13)
        else:
            return json.loads(tag_val)

    @staticmethod
    def onsite_user():
        if ESPUser.objects.filter(username='onsite').exists():
            return ESPUser.objects.get(username='onsite')
        else:
            return None


    @classmethod
    def ajax_autocomplete(cls, data, QObject = None):
        """
        Filter is a dictionary, where the keys are ESPUser model fields
        and the values are the filters on those fields
        (e.g. {})
        """
        #q_name assumes data is a comma separated list of names
        #lastname first
        #q_username is username
        #q_id is id
        #this feels kind of weird because it's selecting
        #from three keys using the same value
        names = data.strip().split(',')
        last = names[0]
        username = names[0]
        idstr = names[0]
        q_names = Q(last_name__istartswith = last.strip())
        if len(names) > 1:
          first = ','.join(names[1:])
          if len(first.strip()) > 0:
            q_names = q_names & Q(first_name__istartswith = first.strip())

        q_username = Q(username__istartswith = username.strip())
        q_id = Q(id__istartswith = idstr.strip())

        query_set = cls.objects.filter(q_names | q_username | q_id)

        if QObject:
            query_set = query_set.filter(QObject).distinct()

        values = query_set.order_by('last_name','first_name','id').values('first_name', 'last_name', 'username', 'id')

        for value in values:
            value['ajax_str'] = '%s, %s (%s)' % (value['last_name'], value['first_name'], value['username'])
        return values

    @classmethod
    def ajax_autocomplete_student(cls, data):
        return cls.ajax_autocomplete(data, QObject = Q(groups=Group.objects.get(name="Student")))

    @classmethod
    def ajax_autocomplete_teacher(cls, data):
        return cls.ajax_autocomplete(data, QObject = Q(groups=Group.objects.get(name="Teacher")))

    @classmethod
    def ajax_autocomplete_approved_teacher(cls, data, prog = None):
        if prog:
            QObject = Q(classsubject__status__gt=0, classsubject__parent_program__id=prog)
        else:
            QObject = Q(classsubject__status__gt=0)
        return cls.ajax_autocomplete(data, QObject)

    def ajax_str(self):
        return "%s, %s (%s)" % (self.last_name, self.first_name, self.username)

    def name(self):
        return u'%s %s' % (self.first_name, self.last_name)

    def name_last_first(self):
        return u'%s, %s' % (self.last_name, self.first_name)

    def nonblank_name(self):
        name = self.name()
        if name.strip() == '': name = self.username
        return name

    def get_email_sendto_address_pair(self):
        """
        Returns the pair of data needed to send an email to the user.
        """
        return (self.email, self.name())

    @staticmethod
    def email_sendto_address(email, name=''):
        """
        Given an email and a name, returns the string used to address mail.
        """
        if name:
            return u'%s <%s>' % (name, email)
        else:
            return u'<%s>' % email

    def get_email_sendto_address(self):
        """
        Returns the string used to address mail to the user.
        """
        return ESPUser.email_sendto_address(self.email, self.name())

    def __cmp__(self, other):
        lastname = cmp(self.last_name.upper(), other.last_name.upper())
        if lastname == 0:
           return cmp(self.first_name.upper(), other.first_name.upper())
        return lastname

    def getLastProfile(self):
        # caching is handled in RegistrationProfile.getLastProfile
        # for coherence w.r.t clearing and more caching
        from esp.program.models import RegistrationProfile
        return RegistrationProfile.getLastProfile(self)

    def get_last_program_with_profile(self):
        # as in getLastProfile, caching is handled in
        # RegistrationProfile.getLastProfile for coherence
        from esp.program.models import RegistrationProfile
        return RegistrationProfile.get_last_program_with_profile(self)

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

        if user.isAdministrator() or user.is_staff or user.is_superuser:
            # Disallow morphing into Administrators.
            # It's too broken, from a security perspective.
            # -- aseering 1/29/2010
            raise ESPError("User '%s' is an administrator; morphing into administrators is not permitted." % user.username, log=False)

        logout(request)
        user.backend = 'esp.utils.auth_backend.ESPAuthBackend'
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
            raise ESPError('Error: You were not another user to begin with!')

        retUrl   = request.session['user_morph']['retUrl']
        new_user = self.get_old(request)

        if not new_user:
            return retUrl

        del request.session['user_morph']
        logout(request)

        old_user = new_user
        old_user.backend = 'esp.utils.auth_backend.ESPAuthBackend'

        login(request, old_user)

        return retUrl

    def get_msg_vars(self, otheruser, key):
        """ This function will be called when rendering a message. """
        if key == 'first_name':
            return otheruser.first_name
        elif key == 'last_name':
            return otheruser.last_name
        elif key == 'name':
            return otheruser.name()
        elif key == 'username':
            return otheruser.username
        elif key == 'recover_url':
            return 'http://%s/myesp/recoveremail/?code=%s' % \
                         (settings.DEFAULT_HOST, otheruser.password)
        elif key == 'recover_query':
            return "?code=%s" % otheruser.password
        return u''

    def getTaughtPrograms(self):
        taught_programs = Program.objects.filter(classsubject__teachers=self)
        taught_programs = taught_programs.distinct()
        return taught_programs

    def getTaughtClasses(self, program = None, include_rejected = False):
        """ Return all the taught classes for this user. If program is specified, return all the classes under
            that class. For most users this will return an empty queryset. """
        if program is None:
            return self.getTaughtClassesAll(include_rejected = include_rejected)
        else:
            return self.getTaughtClassesFromProgram(program, include_rejected = include_rejected)

    @cache_function
    def getTaughtClassesFromProgram(self, program, include_rejected = False):
        from esp.program.models import Program # Need the Class object.
        if not isinstance(program, Program): # if we did not receive a program
            raise ESPError("getTaughtClassesFromProgram expects a Program, not a `"+str(type(program))+"'.")
        else:
            if include_rejected:
                return self.classsubject_set.filter(parent_program = program)
            else:
                return self.classsubject_set.filter(parent_program = program).exclude(status=-10)
    getTaughtClassesFromProgram.depend_on_m2m('program.ClassSubject', 'teachers', lambda cls, teacher: {'self': teacher})
    getTaughtClassesFromProgram.depend_on_row('program.ClassSubject', lambda cls: {'program': cls.parent_program}) # TODO: auto-row-thing...

    @cache_function
    def getTaughtClassesAll(self, include_rejected = False):
        if include_rejected:
            return self.classsubject_set.all()
        else:
            return self.classsubject_set.exclude(status=-10)
    getTaughtClassesAll.depend_on_row('program.ClassSubject', lambda cls: {'self': cls})
    getTaughtClassesAll.depend_on_m2m('program.ClassSubject', 'teachers', lambda cls, teacher: {'self': teacher})

    @cache_function
    def getFullClasses_pretty(self, program):
        full_classes = [cls for cls in self.getTaughtClassesFromProgram(program) if cls.is_nearly_full()]
        return "\n".join([cls.emailcode()+": "+cls.title for cls in full_classes])
    getFullClasses_pretty.depend_on_model('program.ClassSubject') # should filter by teachers... eh.


    def getTaughtSections(self, program = None, include_rejected = False):
        if program is None:
            return self.getTaughtSectionsAll(include_rejected = include_rejected)
        else:
            return self.getTaughtSectionsFromProgram(program, include_rejected = include_rejected)

    @cache_function
    def getTaughtSectionsAll(self, include_rejected = False):
        from esp.program.models import ClassSection
        classes = list(self.getTaughtClassesAll(include_rejected = include_rejected))
        if include_rejected:
            return ClassSection.objects.filter(parent_class__in=classes)
        else:
            return ClassSection.objects.filter(parent_class__in=classes).exclude(status=-10)
    getTaughtSectionsAll.depend_on_model('program.ClassSection')
    getTaughtSectionsAll.depend_on_cache(getTaughtClassesAll, lambda self=wildcard, **kwargs:
                                                              {'self':self})
    @cache_function
    def getTaughtSectionsFromProgram(self, program, include_rejected = False):
        from esp.program.models import ClassSection
        classes = list(self.getTaughtClasses(program, include_rejected = include_rejected))
        if include_rejected:
            return ClassSection.objects.filter(parent_class__in=classes)
        else:
            return ClassSection.objects.filter(parent_class__in=classes).exclude(status=-10)
    getTaughtSectionsFromProgram.get_or_create_token(('program',))
    getTaughtSectionsFromProgram.depend_on_row('program.ClassSection', lambda instance: {'program': instance.parent_program})
    getTaughtSectionsFromProgram.depend_on_cache(getTaughtClassesFromProgram, lambda self=wildcard, program=wildcard, **kwargs:
                                                                              {'self':self, 'program':program})

    def getTaughtTime(self, program = None, include_scheduled = True, round_to = 0.0, include_rejected = False):
        """ Return the time taught as a timedelta. If a program is specified, return the time taught for that program.
            If include_scheduled is given as False, we don't count time for already-scheduled classes.
            Rounds to the nearest round_to (if zero, doesn't round at all). """
        user_sections = self.getTaughtSections(program, include_rejected = include_rejected)
        total_time = timedelta()
        round_to = float( round_to )
        if round_to:
            rounded_hours = lambda x: round_to * round( float( x ) / round_to )
        else:
            rounded_hours = lambda x: float( x )
        for s in user_sections:
            #   don't count cancelled or rejected classes -- Ted
            #   or rejected sections -- lua
            if (include_scheduled or (s.start_time() is None)) and (s.status >= 0 and s.parent_class.status >= 0):
                total_time = total_time + timedelta(hours=rounded_hours(s.duration))
        return total_time

    def getTaughtTimes(self, program = None, exclude = []):
        """ Return the times taught as a set. If a program is specified, return the times taught for that program.
            If exclude is specified (as a list of classes), exclude sections from the specified classes. """
        user_sections = self.getTaughtSections(program)
        times = set()
        for s in user_sections:
            if s.parent_class not in exclude:
                times.update(s.meeting_times.all())
        return times

    @staticmethod
    def getUserFromNum(first, last, num):
        if num == '':
            num = 0
        try:
            num = int(num)
        except:
            raise ESPError('Could not find user "%s %s"' % (first, last))
        users = ESPUser.objects.filter(last_name__iexact = last,
                                    first_name__iexact = first).order_by('id')
        if len(users) <= num:
            raise ESPError('"%s %s": Unknown User' % (first, last), log=False)
        return users[num]

    @cache_function
    def getTypes(use_tag=True):
        """
        Get a list of the different roles an ESP user can have. By default
        there are five roles, but there can be more. Returns
        ['Student','Teacher','Educator','Guardian','Volunteer'] by default. If
        use_tag is False, always returns the default roles, and ignores the Tag
        override.
        """
        return [x[0] for x in ESPUser.getAllUserTypes(use_tag=use_tag)]
    getTypes.depend_on_model(Tag)
    getTypes = staticmethod(getTypes)

    @staticmethod
    def getAllOfType(strType, QObject = True):
        if strType not in ESPUser.getTypes():
            raise ESPError("Invalid type to find all of.")

        Q_useroftype      = Q(groups__name=strType)

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
        if program.hasModule('AvailabilityModule'):
            valid_events = Event.objects.filter(useravailability__user=self, program=program).order_by('start')
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
    getAvailableTimes.depend_on_m2m('program.ClassSection', 'meeting_times', lambda sec, event: {'program': sec.parent_program})
    getAvailableTimes.depend_on_m2m('program.Program', 'program_modules', lambda prog, pm: {'program': prog})
    getAvailableTimes.depend_on_row('users.UserAvailability', lambda ua:
                                        {'program': ua.event.program,
                                            'self': ua.user})
    # Should depend on Event as well... IDs are safe, but not necessarily stored objects (seems a common occurence...)
    # though Event shouldn't change much

    def clearAvailableTimes(self, program):
        """ Clear this teacher's class availability (but not interviews, etc.) for a program """
        try:
            class_time_block_event_type = EventType.objects.get(description='Class Time Block')
        except EventType.DoesNotExist:
            raise ESPError('There is no Class Time Block event type; this should always be there!')
        self.useravailability_set.filter(event__program=program, event__event_type=class_time_block_event_type).delete()

    def addAvailableTime(self, program, timeslot, role=None):
        #   Because the timeslot has a program, the program is unnecessary.
        #   Default to teacher mode
        if role is None:
            role = Group.objects.get_or_create(name='Teacher')[0]
        new_availability, created = UserAvailability.objects.get_or_create(user=self, event=timeslot, role=role)
        new_availability.save()

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
            scrmi = program.studentclassregmoduleinfo
            verb_list = [v.name for v in scrmi.reg_verbs()]
        else:
            verb_list = ['Applied']

        return self.getClasses(program, verbs=verb_list)

    def getEnrolledClasses(self, program=None):
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

        if verbs:
            rts = RegistrationType.objects.filter(name__in=verbs)
        else:
            rts = RegistrationType.objects.all()

        if program:
            return ClassSection.objects.filter(id__in=self.studentregistration_set.filter(StudentRegistration.is_valid_qobject(), relationship__in=rts).values_list('section', flat=True)).filter(parent_class__parent_program=program)
        else:
            return ClassSection.objects.filter(id__in=self.studentregistration_set.filter(StudentRegistration.is_valid_qobject(), relationship__in=rts).values_list('section', flat=True))

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
    getEnrolledSectionsFromProgram.depend_on_row('program.StudentRegistration', lambda reg: {'self': reg.user})
    getEnrolledSectionsFromProgram.depend_on_cache('program.ClassSection.timeslot_ids', lambda self=wildcard, **kwargs: {})

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
    getFirstClassTime.depend_on_row('program.StudentRegistration', lambda reg: {'self': reg.user})

    def can_skip_phase_zero(self, program):
        return Permission.user_has_perm(self, 'OverridePhaseZero', program)

    def getRegistrationPriority(self, prog, timeslots):
        """ Finds the highest available priority level for this user across the supplied timeslots.
            Returns 0 if the student is already enrolled in one or more of the timeslots. """
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

    def isEnrolledInClass(self, clsObj, request=None):
        return clsObj.students().filter(id=self.id).exists()

    def canRegToFullProgram(self, program):
        return Permission.user_has_perm(self, 'OverrideFull', program)

    @cache_function
    def appliedFinancialAid(self, program):
        return self.financialaidrequest_set.all().filter(program=program, done=True).count() > 0
    #   Invalidate cache when any of the user's financial aid requests are changed
    appliedFinancialAid.depend_on_row('program.FinancialAidRequest', lambda fr: {'self': fr.user})
    appliedFinancialAid.depend_on_row('accounting.FinancialAidGrant', lambda fr: {'self': fr.request.user})

    @cache_function
    def hasFinancialAid(self, program):
        from esp.accounting.controllers import IndividualAccountingController
        iac = IndividualAccountingController(program, self)
        if iac.amount_finaid() > 0:
            return True
        else:
            return False
    hasFinancialAid.depend_on_row('program.FinancialAidRequest', lambda fr: {'self': fr.user})

    def isOnsite(self, program=None):
        """Determine if the user is an authorized onsite user for the program.

        :param program:
            Check for permission to access onsite for this program.
            If None, check for permission to access onsite for all programs.
        :type program:
            `Program` or None
        """
        return (
            (getattr(self, 'onsite_local', False) is True) or
            Permission.user_has_perm(
                self,
                'Onsite',
                program=program,
                program_is_none_implies_all=True,
            )
        )

    def recoverPassword(self):
        # generate the ticket, send the email.
        from django.contrib.sites.models import Site
        from django.conf import settings

        # we have a lot of users with no email (??)
        #  let's at least display a sensible error message
        if self.email.strip() == '':
            raise ESPError('User %s has blank email address; cannot recover password. Please contact webmasters to reset your password.' % self.username)

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
        msgtext = t.render({'user': self,
                            'ticket': ticket,
                            'domainname': domainname,
                            'orgname': settings.ORGANIZATION_SHORT_NAME,
                            'institution': settings.INSTITUTION_NAME})

        # Do NOT fail_silently. We want to know if there's a problem.
        send_mail(subject, msgtext, from_email, to_email)


    @cache_function
    def isAdministrator(self, program=None):
        """Determine if the user is an admin for the program.

        :param program:
            Check for admin privileges for this program.
            If None, check for global admin privileges.
        :type program:
            `Program` or None
        """
        if self.is_anonymous() or self.id is None: return False
        is_admin_role = self.groups.filter(name="Administrator").exists()
        if is_admin_role: return True
        quser = Q(user=self) | Q(user=None, role__in=self.groups.all())
        # Unexpectedly and unfortunately, program__in=[None, program] doesn't
        # find objects with program=None.
        qprogram = Q(program=None) | Q(program=program)
        return Permission.objects.filter(
                        quser & qprogram & Permission.is_valid_qobject(),
                        permission_type="Administer",
        ).exists()
    isAdministrator.get_or_create_token(('self',))
    isAdministrator.get_or_create_token(('program',))
    isAdministrator.depend_on_row('users.ESPUser', lambda user: {'self': user})
    isAdministrator.depend_on_m2m('users.ESPUser', 'groups', lambda user, group: {'self': user})
    # if the permission has null user and non-null group, expire all caches,
    # otherwise expire only the one for the relevant user.
    isAdministrator.depend_on_row('users.Permission', lambda perm:
                                  {'self': perm.user}
                                  if perm.user is not None
                                  or perm.role is None
                                  else {'self': wildcard})
    isAdmin = isAdministrator

    @cache_function
    def getAllUserTypes(use_tag=True):
        """
        Get the list of all user types, along with their metadata (label and
        profile form). By default returns DEFAULT_USER_TYPES. Allow user_types
        Tag to override this struct. The Tag can remove user types as well as
        adding/updating them. So, if you set the Tag, be sure to include all
        of the user types you want.

        If use_tag is False, always returns DEFAULT_USER_TYPES, and ignores the
        Tag override.
        """
        user_types = DEFAULT_USER_TYPES
        if use_tag:
            user_types = json.loads(Tag.getTag('user_types'))
        return user_types
    getAllUserTypes.depend_on_model(Tag)
    getAllUserTypes = staticmethod(getAllUserTypes)

    def getUserTypes(self):
        """ Return the set of types for this user """
        return self.groups.all().order_by('name').values_list("name",flat=True)

    @staticmethod
    def create_membership_method(user_class):
        """
        Creates the methods such as isTeacher that determines whether
        or not the user is a member of that user class.
        """
        def _new_method(user):
            return user.is_user_type(user_class)
        _new_method.__name__    = 'is%s' % str(user_class)
        _new_method.__doc__     = "Returns ``True`` if the user is a %s and False otherwise." % user_class
        return _new_method

    def is_user_type(self, user_class):
        """
        Determines whether the user is a member of user_class.
        """
        property_name = '_userclass_%s' % user_class
        if not hasattr(self, property_name):
            role_name = {'Officer': 'Administrator'}.get(user_class, user_class)
            setattr(self, property_name, self.groups.filter(name=role_name).exists())
        return getattr(self, property_name)

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
        self.groups.add(Group.objects.get_or_create(name="Volunteer")[0])

    def makeRole(self, role_name):
        self.groups.add(Group.objects.get_or_create(name=role_name)[0])

    def removeRole(self, role_name):
        self.groups.remove(Group.objects.get_or_create(name=role_name)[0])

    def hasRole(self, role_name):
        return self.groups.filter(name=role_name).exists()

    def canEdit(self, cls):
        """Returns if the user can edit the class

A user can edit a class if they can administrate the program or if they
are a teacher of the class"""
        if self in cls.get_teachers(): return True
        return self.isAdmin(cls.parent_program)

    def getVolunteerOffers(self, program):
        return self.volunteeroffer_set.filter(request__program=program)

    @staticmethod
    def current_schoolyear(now=None):
        """
        Get the school year for the current time or a given time.

        School year NNNN is defined as the period between August
        NNNN-1 and July NNNN.
        """
        if now is None:
            now = date.today()
        curyear = now.year
        try:
            # An error here can cause a good chunk of the site to break,
            # so we'll just catch this if it fails and fall back on the default
            d = datetime.strptime(Tag.getTag('grade_increment_date'), '%Y-%m-%d').date().replace(year=curyear)
        except:
            d = date(curyear, 7, 31)
        if d > now:
            schoolyear = curyear
        else:
            schoolyear = curyear + 1
        return schoolyear

    @staticmethod
    @cache_function
    def program_schoolyear(program):
        """
        Get the school year for a given program.

        This is determined by the current_schoolyear (see above) of
        the first day of the program, and is used to calculate a
        student's effective grade for the program.

        This can be modified by setting the program tag
        "increment_default_grade_levels", which increments the
        program's effective school year.
        """
        # "now" is actually whenever the program ran or will run
        dates = program.dates()
        if len(dates) >= 1:
            now = dates[0]
        else:
            now = None
        schoolyear = ESPUser.current_schoolyear(now)
        schoolyear += program.incrementGrade() # adds 1 if appropriate tag is set; else does nothing
        return schoolyear
    program_schoolyear.__func__.depend_on_row(Tag, lambda tag: {'program': tag.target})
    program_schoolyear.__func__.depend_on_row(Event, lambda event: {'program': event.program})

    @cache_function
    def getYOG(self, program=None, assume_student=False):
        """
        Get a student's year of graduation.

        If program is given, use the registration profile from that
        program to look up the graduation year; otherwise, use the
        latest one.

        assume_student will save us a database hit if the user is a student,
        but cost us at least one and possibly several if they're not.
        """
        if assume_student or self.isStudent():
            if program is None:
                regProf = self.getLastProfile()
            else:
                from esp.program.models import RegistrationProfile
                regProf = RegistrationProfile.getLastForProgram(self, program)
            if regProf and regProf.student_info:
                if regProf.student_info.graduation_year:
                    return regProf.student_info.graduation_year
        return None
    getYOG.get_or_create_token(('self',))
    getYOG.depend_on_row('users.StudentInfo', lambda info: {'self': info.user})

    @cache_function
    def getGrade(self, program=None, assume_student=False):
        """Get the grade of this student.

        Get the grade at the time of the program, or for the current school
        year if program is None.

        assume_student will save us a database hit if the user is a student,
        but cost us at least one and possibly several if they're not.  See
        ESPUser.getYOG.
        """
        grade = 0
        yog = self.getYOG(program, assume_student)
        schoolyear = None
        if program is not None:
            schoolyear = ESPUser.program_schoolyear(program)
        if yog is not None:
            grade = ESPUser.gradeFromYOG(yog, schoolyear)
        return grade
    #   The cache will need to be cleared once per academic year.
    getGrade.get_or_create_token(('self',))
    getGrade.get_or_create_token(('program',))
    getGrade.depend_on_cache(getYOG, lambda self=wildcard, program=wildcard, **kwargs: {'self': self, 'program': program})
    getGrade.depend_on_cache(program_schoolyear.__func__, lambda self=wildcard, **kwargs: {'program': self})

    @staticmethod
    def gradeFromYOG(yog, schoolyear=None):
        if schoolyear == None:
            schoolyear = ESPUser.current_schoolyear()
        try:
            yog        = int(yog)
        except:
            return 0
        return schoolyear + 12 - yog

    @staticmethod
    def YOGFromGrade(grade, schoolyear=None):
        if schoolyear is None:
            schoolyear = ESPUser.current_schoolyear()
        try:
            grade = int(grade)
        except:
            return 0

        return schoolyear + 12 - grade

    def set_student_grad_year(self, grad_year):
        """ Update the user's graduation year if they are a student. """

        #   Check that the user is a student.
        #   (We could raise an error, but I don't think it's a huge problem
        #   if this function is called accidentally on a non-student.)
        if not self.isStudent():
            return

        #   Retrieve the user's most recent registration profile and create a StudentInfo if needed.
        profile = self.getLastProfile()
        if profile.student_info is None:
            profile.student_info = StudentInfo(user=self)
            profile.save()

        #   Update the graduation year.
        student_info = profile.student_info
        student_info.graduation_year = int(grad_year)
        student_info.save()

    def set_grade(self, grade):
        """ Convenience function for setting a student's grade based on the
            current school year. """
        self.set_student_grad_year(ESPUser.YOGFromGrade(int(grade)))

    @staticmethod
    def getRankInClass(student, subject, default=10):
        from esp.program.models.app_ import StudentAppQuestion, StudentAppResponse, StudentAppReview, StudentApplication
        from esp.program.models import StudentRegistration
        if isinstance(subject, int):
            subject = ClassSubject.objects.get(id=subject)
        if not StudentAppQuestion.objects.filter(subject=subject).count():
            return 10
        elif StudentRegistration.objects.filter(section__parent_class=subject, relationship__name="Rejected",end_date__gte=datetime.now(),user=student).exists() or not StudentApplication.objects.filter(user=student, program__classsubject = subject).exists() or not StudentAppResponse.objects.filter(question__subject=subject, studentapplication__user=student).exists():
            return 1
        for sar in StudentAppResponse.objects.filter(question__subject=subject, studentapplication__user=student):
            if not len(sar.response.strip()):
                return 1
        rank = max(list(StudentAppReview.objects.filter(studentapplication__user=student, studentapplication__program__classsubject=subject, reviewer__in=subject.teachers()).values_list('score', flat=True)) + [-1])
        if rank == -1:
            rank = default
        return rank

class ESPUser(User, BaseESPUser):
    """ Create a user of the ESP Website
    This user extends the auth.User of django"""

    class Meta:
        proxy = True
        verbose_name = 'ESP User'

    def makeAdmin(self):
        """
        Make the user an Adminstrator and a Django superuser.
        """
        # Django auth
        self.is_staff = True
        self.is_superuser = True
        self.makeRole("Administrator")
        self.save()

    def get_absolute_url(self):
        return "/manage/userview?username="+self.username

class AnonymousESPUser(BaseESPUser, AnonymousUser):
    pass

@dispatch.receiver(signals.post_save, sender=User,
                     dispatch_uid='make_admin_save')
def make_admin_save(sender, instance, **kwargs):
    """
    External scripts like the createsuperuser management command sometimes add
    the is_superuser flag to a User object. This receiver intercepts saves of
    User objects and ensures that ESPUser-specific actions, such as adding the
    user to the Administrators group, are also applied.

    Code that references ESPUser instead of User does not trigger this receiver.
    These callers should be explicit and call ESPUser.make_admin() if needed.
    """
    if instance.is_superuser:
        espuser = ESPUser.objects.get(id=instance.id)
        espuser.makeAdmin()

@dispatch.receiver(signals.pre_save, sender=ESPUser,
                   dispatch_uid='update_email_save')
def update_email_save(**kwargs):
    kwargs['deleted']=False
    return update_email(**kwargs)


@dispatch.receiver(signals.pre_delete, sender=ESPUser,
                   dispatch_uid='update_email_delete')
def update_email_delete(**kwargs):
    kwargs['deleted']=True
    return update_email(**kwargs)


@enable_with_setting(settings.USE_MAILMAN)
def update_email(**kwargs):
    """Update a user if they changed their email.

    With the exception of separate mailman-only subscriptions, we want the
    mailman announcements list to consist of the email addresses of all active users.
    When there is only one user with a given email address, this is easy.  When
    there are multiple users with the same email address, we handle this as
    follows:
    * If one of the users changes their email address, keep both the old and
      new addresses.  If the user has changed email addresses, then sending to
      the old one probably won't hurt; if the user is a student switching to
      their own email address from a parent's, we definitely want to keep both.
    * If one of the users deletes or deactivates their account, deactivate all
      other accounts with the same email address.  This is slightly sketchy
      because it allows one user to take actions on behalf of another, but it
      is likely the desired behavior, and since a user shouldn't be able to get
      here without confirming their email, it should be okay.  In any case, it
      can be reverted by a site admin (or even by the user themself, by doing a
      new confirmation email).
    """
    from esp import mailman
    deleted = kwargs['deleted']
    if deleted:
        # If for some reason we delete an already deactivated user, we'll
        # remove them from lists anyway just in case.  So we ignore is_active
        # here.
        old_user = kwargs['instance']
        old_email = old_user.email
        new_email = None
    else:
        new_user = kwargs['instance']
        if new_user.id is None:
            # It's a newly created user, don't do anything.
            return
        old_user = ESPUser.objects.get(id=new_user.id)
        old_email = old_user.email if old_user.is_active else None
        new_email = new_user.get_email_sendto_address() if new_user.is_active else None
        if (old_user.email == new_user.email) and (old_user.is_active == new_user.is_active):
            # They didn't change their email and didn't activate/deactivate,
            # don't do anything.
            return


    # Now we have set old_email and new_email; if either is not None, the
    # corresponding old_user or new_user will also exist.  Now actually do
    # things.
    group_map = {
            'Student': 'announcements',
            'Guardian': 'announcements',
            'Educator': 'announcements',
            'Teacher': 'teachers',
    }
    other_users = ESPUser.objects.filter(email=old_email).exclude(id=old_user.id)
    groups = (new_user or old_user).groups.values_list('name', flat=True)
    is_admin = (new_user or old_user).isAdministrator()
    if old_email is None:
        # We will never get a newly created user here, because we only fire on
        # *activation*.  So we can use new_user.groups to figure out the lists
        # to which they should be added.
        for g in groups:
            if g in group_map:
                mailman.add_list_member(group_map[g], new_email)
    elif new_email is None:
        groups_to_deactivate = set(groups)
        if 'Student' in groups or 'Guardian' in groups or 'Educator' in groups:
            # If they are a student, guardian, or educator, deactivate all such
            # accounts.  This seems like it makes the most sense.
            groups_to_deactivate.update(['Student', 'Guardian', 'Educator'])
        if not is_admin:
            # If they're an admin, they might be doing something weird, so
            # don't deactivate any of their accounts.
            users_to_deactivate = other_users.filter(groups__name__in=groups_to_deactivate)
            # QuerySet.update() does not call save signals, so this won't be
            # circular.  If we or django ever patch it to do so, we will need
            # to be more careful here.
            users_to_deactivate.update(is_active=False)
        # Only remove them from group-based lists; keep them on program and
        # class lists.
        for l in set(group_map.values()):
            mailman.remove_list_member(l, old_email)
    else:
        # Transition all their lists, not just the group-based ones.  Rather
        # than try to guess which lists that is, we can just ask mailman.
        mailman_lists = mailman.lists_containing(old_email)
        if other_users.exists():
            # If this is not their only account, only transition lists that
            # make sense for this account type.
            lists = []
            for l in mailman_lists:
                if l in group_map.values():
                    # A role-based list: only transition them if they are an
                    # appropriate type of account.
                    if any(group_map.get(g) == l for g in groups) or is_admin:
                        lists.append(l)
                elif 'teachers' in l:
                    if 'Teacher' in groups or is_admin:
                        lists.append(l)
                elif 'class' in l or 'students' in l:
                    if 'Teacher' in groups or 'Student' in groups or is_admin:
                        lists.append(l)
                elif 'parents' in l or 'guardians' in l:
                    # We don't currently (as of 7/2014) autocreate these lists,
                    # but we sometimes manually create them, and may one day
                    # autocreate them.  Handling these correctly would be a bit
                    # trickier because they don't actually come from users,
                    # they come from students' emergency contacts.
                    # Nonetheless, updating the list based on the account is
                    # probably good enough.
                    if 'Guardian' in groups or is_admin:
                        lists.append(l)
                else:
                    # Some list we don't really understand, quite possibly a
                    # manually-created one.  If in doubt, let's transition
                    # their membership.
                    lists.append(l)
        else:
            lists = mailman_lists
        for l in lists:
            mailman.add_list_member(l, new_email)
        if not other_users.exists():
            for l in lists:
                mailman.remove_list_member(l, old_email)


class StudentInfo(models.Model):
    """ ESP Student-specific contact information """
    user = AjaxForeignKey(ESPUser, blank=True, null=True)
    graduation_year = models.PositiveIntegerField(blank=True, null=True)
    k12school = AjaxForeignKey('K12School', help_text='Begin to type your school name and select your school if it comes up.', blank=True, null=True)
    school = models.CharField(max_length=256,blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=32,blank=True,null=True)
    studentrep = models.BooleanField(blank=True, default = False)
    studentrep_expl = models.TextField(blank=True, null=True)
    heard_about = models.TextField(blank=True, null=True)
    food_preference = models.TextField(blank=True, null=True)
    shirt_size = models.TextField(blank=True, null=True)
    shirt_type = models.TextField(blank=True, null=True)

    medical_needs = models.TextField(blank=True, null=True)

    # Deprecated, but left here so as not to remove Chicago's existing data.
    schoolsystem_id = models.CharField(max_length=32, blank=True, null=True)
    schoolsystem_optout = models.BooleanField(default=False)
    post_hs = models.TextField(default='', blank=True)
    transportation = models.TextField(default='', blank=True)

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
            value['user'] = ESPUser.objects.get(id=value['user'])
            value['ajax_str'] = '%s - %s %d' % (value['user'].ajax_str(), value['school'], value['graduation_year'])
        return values

    def ajax_str(self):
        return "%s - %s %d" % (self.user.ajax_str(), self.school, self.graduation_year)

    def updateForm(self, form_dict):
        form_dict['graduation_year'] = self.graduation_year
        #   Display data from school field in the k12school box if there's no k12school data.
        if self.k12school:
            form_dict['k12school']       = self.k12school_id
        else:
            form_dict['k12school']   = self.school
        form_dict['school']          = self.school
        form_dict['dob']             = self.dob
        form_dict['gender']          = self.gender
        if Tag.getBooleanTag('show_student_tshirt_size_options'):
            form_dict['shirt_size']      = self.shirt_size
        if Tag.getBooleanTag('studentinfo_shirt_type_selection'):
            form_dict['shirt_type']      = self.shirt_type
        if Tag.getBooleanTag('show_student_vegetarianism_options'):
            form_dict['food_preference'] = self.food_preference
        form_dict['heard_about']      = self.heard_about
        form_dict['studentrep_expl'] = self.studentrep_expl
        form_dict['studentrep']      = self.user.hasRole('StudentRep')
        form_dict['medical_needs'] = self.medical_needs
        form_dict['transportation'] = self.transportation
        return form_dict

    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a StudentInfo record """

        if regProfile.student_info is None:
            studentInfo = StudentInfo()
        else:
            studentInfo = regProfile.student_info
        if not studentInfo.user:
            studentInfo.user = curUser
        elif studentInfo.user != curUser: # this should never happen, but you never know....
            raise ESPError("Your registration profile is corrupted. Please contact" +
                            "{}".format(settings.DEFAULT_EMAIL_ADDRESSES['support']) +
                            " with your name and username in the message to " +
                            "correct this issue.")

        studentInfo.graduation_year = new_data['graduation_year']
        try:
            if isinstance(new_data.get('k12school'), K12School):
                studentInfo.k12school = new_data.get('k12school')
            else:
                if isinstance(new_data.get('k12school'), int):
                    studentInfo.k12school = K12School.objects.get(id=int(new_data.get('k12school')))
                else:
                    studentInfo.k12school = K12School.objects.filter(name__icontains=new_data.get('k12school'))[0]

        except:
            logger.warning('Could not find k12school for "%s"', new_data.get('k12school'))
            studentInfo.k12school = None

        studentInfo.school          = new_data.get('school') if not studentInfo.k12school else studentInfo.k12school.name
        studentInfo.dob             = new_data.get('dob')
        studentInfo.gender          = new_data.get('gender', None)

        studentInfo.heard_about      = new_data.get('heard_about', '')

        if 'shirt_size' in new_data and 'shirt_type' in new_data:
            studentInfo.shirt_size      = new_data['shirt_size']
            studentInfo.shirt_type      = new_data['shirt_type']

        if 'food_preference' in new_data:
            studentInfo.food_preference      = new_data['food_preference']


        studentInfo.studentrep = new_data.get('studentrep', False)
        studentInfo.studentrep_expl = new_data.get('studentrep_expl', '')

        studentInfo.medical_needs = new_data.get('medical_needs', '')
        studentInfo.transportation = new_data.get('transportation', '')
        studentInfo.save()
        if new_data.get('studentrep', False):
            #   Email membership notifying them of the student rep request.
            subj = '[%s Membership] Student Rep Request: %s %s' % (settings.ORGANIZATION_SHORT_NAME, curUser.first_name, curUser.last_name)
            to_email = [settings.DEFAULT_EMAIL_ADDRESSES['membership']]
            from_email = 'ESP Profile Editor <regprofile@%s>' % settings.DEFAULT_HOST
            t = loader.get_template('email/studentreprequest')
            msgtext = t.render(Context({'user': curUser, 'info': studentInfo, 'prog': regProfile.program}))
            send_mail(subj, msgtext, from_email, to_email, fail_silently = True)

            #   Add the user bit representing a student rep request.
            #   The membership coordinator has to make the 'real' student rep bit.
            curUser.makeRole("StudentRep")
        else:
            curUser.removeRole("StudentRep")
        return studentInfo

    def getSchool(self):
        """ Obtain a string representation of the student's school  """
        if self.k12school:
            return self.k12school
        elif self.school:
            return self.school
        else:
            return None

    getSchool.short_description = "School"

    def __unicode__(self):
        username = "N/A"
        if self.user != None:
            username = self.user.username
        return u'ESP Student Info (%s) -- %s' % (username, unicode(self.school))

    def get_absolute_url(self):
        return self.user.get_absolute_url()

AFFILIATION_UNDERGRAD = 'Undergrad'
AFFILIATION_GRAD = 'Grad'
AFFILIATION_POSTDOC = 'Postdoc'
AFFILIATION_OTHER = 'Other'
AFFILIATION_NONE = 'None'

class TeacherInfo(models.Model, CustomFormsLinkModel):
    """ ESP Teacher-specific contact information """

    #customforms definitions
    form_link_name = 'TeacherInfo'
    link_fields_list = [
        ('graduation_year', 'Graduation year'),
        ('from_here', 'Current student checkbox'),
        ('affiliation', 'School affiliation type'),
        ('is_graduate_student', 'Graduate student status'),
        ('college', 'School/employer'),
        ('major', 'Major/department'),
        ('bio', 'Biography'),
        ('shirt_size', 'Shirt size'),
        ('shirt_type', 'Shirt type'),
    ]
    link_fields_widgets = {
        'from_here': NullRadioSelect,
        'is_graduate_student': NullCheckboxSelect,
    }

    user = AjaxForeignKey(ESPUser, blank=True, null=True)
    graduation_year = models.CharField(max_length=4, blank=True, null=True)
    affiliation = models.CharField(max_length=100, blank=True)
    from_here = models.NullBooleanField(null=True)
    is_graduate_student = models.NullBooleanField(blank=True, null=True)
    college = models.CharField(max_length=128,blank=True, null=True)
    major = models.CharField(max_length=32,blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    shirt_size = models.TextField(blank=True, null=True)
    shirt_type = models.TextField(blank=True, null=True)

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
            value['user'] = ESPUser.objects.get(id=value['user'])
            value['ajax_str'] = u'%s - %s %s' % (value['user'].ajax_str(), value['college'], value['graduation_year'])
        return values

    def ajax_str(self):
        return u'%s - %s %s' % (self.user.ajax_str(), self.college, self.graduation_year)

    def updateForm(self, form_dict):
        form_dict['graduation_year'] = self.graduation_year
        form_dict['affiliation'] = self.affiliation
        form_dict['major']           = self.major
        form_dict['shirt_size']      = self.shirt_size
        form_dict['shirt_type']      = self.shirt_type
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
        teacherInfo.affiliation = new_data['affiliation']
        affiliation = teacherInfo.affiliation.split(':', 1)[0]
        teacherInfo.from_here           = affiliation in (AFFILIATION_UNDERGRAD, AFFILIATION_GRAD, AFFILIATION_POSTDOC, AFFILIATION_OTHER)
        teacherInfo.is_graduate_student = (affiliation == AFFILIATION_GRAD)
        if affiliation == AFFILIATION_NONE:
            teacherInfo.college         = teacherInfo.affiliation.split(':', 1)[1]
        else:
            teacherInfo.college         = ''
        teacherInfo.major               = new_data['major']
        teacherInfo.shirt_size          = new_data['shirt_size']
        teacherInfo.shirt_type          = new_data['shirt_type']
        teacherInfo.save()
        return teacherInfo

    def __unicode__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return u'ESP Teacher Info (%s)' % username

    def get_absolute_url(self):
        return self.user.get_absolute_url()

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
            value['user'] = ESPUser.objects.get(id=value['user'])
            value['ajax_str'] = '%s - %s %d' % (value['user'].ajax_str(), value['year_finished'], value['num_kids'])
        return values

    def ajax_str(self):
        return "%s - %s %d" % (self.user.ajax_str(), self.year_finished, self.num_kids)

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
        return u'ESP Guardian Info (%s)' % username

    def get_absolute_url(self):
        return self.user.get_absolute_url()

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
            value['user'] = ESPUser.objects.get(id=value['user'])
            value['ajax_str'] = '%s - %s %s' % (value['user'].ajax_str(), value['position'], value['school'])
        return values

    def ajax_str(self):
        return "%s - %s at %s" % (self.user.ajax_str(), self.position, self.school)

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

    def getSchool(self):
        """ Obtain a string representation of the educator's school  """
        if self.k12school:
            return self.k12school
        elif self.school:
            return self.school
        else:
            return None
    getSchool.short_description = "School"

    def __unicode__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return u'ESP Educator Info (%s)' % username

    def get_absolute_url(self):
        return self.user.get_absolute_url()

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
            raise ESPError('%s should be a valid decimal number!' % distance)

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
        return u'%s (%s, %s)' % (self.zip_code,
                                self.longitude,
                                self.latitude)



class ZipCodeSearches(models.Model):
    zip_code = models.ForeignKey(ZipCode)
    distance = models.DecimalField(max_digits = 15, decimal_places = 3)
    zipcodes = models.TextField()

    class Meta:
        app_label = 'users'
        db_table = 'users_zipcodesearches'
        verbose_name_plural = 'Zip Code Searches'

    def __unicode__(self):
        return u'%s Zip Codes that are less than %s miles from %s' % \
               (len(self.zipcodes.split(',')), self.distance, self.zip_code)

class ContactInfo(models.Model, CustomFormsLinkModel):
    """ ESP-specific contact information for (possibly) a specific user """

    #customforms definitions
    form_link_name = 'ContactInfo'
    link_fields_list = [
        ('phone_day','Phone number'),
        ('e_mail','Email address'),
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

    user = AjaxForeignKey(ESPUser, blank=True, null=False)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    e_mail = models.EmailField('Email address', blank=True, null=True, max_length=75)
    phone_day = PhoneNumberField('Home phone',blank=True, null=True)
    phone_cell = PhoneNumberField('Cell phone',blank=True, null=True)
    receive_txt_message = models.BooleanField(default=False)
    phone_even = PhoneNumberField('Alternate phone',blank=True, null=True)
    address_street = models.CharField('Street address',max_length=100,blank=True, null=True)
    address_city = models.CharField('City',max_length=50,blank=True, null=True)
    address_state = models.CharField('State',max_length=32,blank=True, null=True)
    address_zip = models.CharField('Zip code',max_length=5,blank=True, null=True)
    address_postal = models.TextField(blank=True,null=True)
    address_country = models.CharField('Country', max_length=2, choices=sorted(country_names.items(), key = lambda x: x[1]), default='US')
    undeliverable = models.BooleanField(default=False)

    class Meta:
        app_label = 'users'
        db_table = 'users_contactinfo'

    def name(self):
        return u'%s %s' % (self.first_name, self.last_name)

    email = property(lambda self: self.e_mail)

    def get_email_sendto_address_pair(self):
        """
        Returns the pair of data needed to send an email to the contact.
        """
        return (self.email, self.name())

    def get_email_sendto_address(self):
        """
        Returns the string used to address mail to the contact.
        """
        return ESPUser.email_sendto_address(self.email, self.name())

    def address(self):
        return u'%s, %s, %s %s' % \
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
    def addOrUpdate(curUser, regProfile, new_data, contactInfo, prefix=''):
        """ adds or updates a ContactInfo record """
        if contactInfo is None:
            contactInfo = ContactInfo()
        for i in contactInfo.__dict__.keys():
            if i != 'user_id' and i != 'id' and prefix+i in new_data:
                contactInfo.__dict__[i] = new_data[prefix+i]
        contactInfo.user = curUser
        contactInfo.save()
        return contactInfo

    def updateForm(self, form_data, prepend=''):
        newkey = self.__dict__
        for key, val in newkey.items():
            if val not in [None, ''] and key != 'id':
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

    def get_absolute_url(self):
        return self.user.get_absolute_url()

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
        help_text=mark_safe('A set of contact information for this school. Type to search by name (Last, First), or <a href="/admin/users/contactinfo/add/">go edit a new one</a>.'))
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
            return u'%s in %s, %s' % (self.name, self.contact.address_city,
                                       self.contact.address_state)
        else:
            return u'%s' % self.name

    @classmethod
    def choicelist(cls, other_help_text=''):
        if other_help_text:
            other_help_text = u' (%s)' % other_help_text
        o = cls.objects.other()
        lst = [ ( x.id, x.name ) for x in cls.objects.most() ]
        lst.append( (o.id, o.name + other_help_text) )
        return lst


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
            raise ESPError('Invalid Q object stored in database.')

        #   Do not include users if they have disabled their account.
        if restrict_to_active and (self.item_model.find('auth.models.User') >= 0 or self.item_model.find('esp.users.models.ESPUser') >= 0):
            QObj = QObj & Q(is_active=True)

        return QObj

    def set_Q(self, q_filter, item_model=None, description='', should_save=True, restrict_to_active=True):
        """
        q_filter - The new filter to set.
        item_model - The new item model, or None if it should stay the same.
        description - The new filter description.
        should_save - If True (default), this PQF will be saved after setting the new filter.
        restrict_to_active - If True (default) and the filter is on users, automatically add an is_active=True filter.
        """
        if item_model is None:
            item_model = self.item_model
        self.item_model = str(item_model)

        if restrict_to_active and (self.item_model.find('auth.models.User') >= 0 or self.item_model.find('esp.users.models.ESPUser') >= 0):
            q_filter = q_filter & Q(is_active=True)

        import hashlib
        dumped_filter = pickle.dumps(q_filter)
        sha1_hash = hashlib.sha1(dumped_filter).hexdigest()

        self.q_filter = dumped_filter
        self.sha1_hash = sha1_hash
        self.useful_name = description

        if should_save:
            self.save()

        return self

    def getList(self, module):
        """ This will actually return the list generated from the filter applied
            to the live database. You must supply the model. If the model is not matched,
            it will become an error. """
        if str(module) != str(self.item_model):
            raise ESPError('The module given does not match that of the persistent entry.')

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
        return str(self.useful_name) + " (" + str(self.id) + ")"


class PasswordRecoveryTicket(models.Model):
    """ A ticket for changing your password. """
    RECOVER_KEY_LEN = 30
    RECOVER_EXPIRE = 2 # number of days before it expires
    SYMBOLS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

    user = models.ForeignKey(ESPUser)
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

class Record(models.Model):
    #To make these better to work with in the admin panel, and to have a
    #well defined set of possibilities, we'll use a set of choices
    #if you want to use this model for an additional thing,
    #add it as a choice
    EVENT_CHOICES=(
        ("student_survey", "Completed student survey"),
        ("teacher_survey", "Completed teacher survey"),
        ("reg_confirmed", "Confirmed registration"),
        ("attended", "Attended program"),
        ("checked_out", "Checked out of program"),
        ("conf_email","Was sent confirmation email"),
        ("teacher_quiz_done","Completed teacher quiz"),
        ("paid","Paid for program"),
        ("med","Submitted medical form"),
        ("med_bypass","Recieved medical bypass"),
        ("liab","Submitted liability form"),
        ("onsite","Registered for program onsite"),
        ("schedule_printed","Printed student schedule onsite"),
        ("teacheracknowledgement","Did teacher acknowledgement"),
        ("studentacknowledgement", "Did student acknowledgement"),
        ("lunch_selected","Selected a lunch block"),
        ("extra_form_done","Filled out Custom Form"),
        ("extra_costs_done","Filled out Student Extra Costs Form"),
        ("donation_done", "Filled out Donation Form"),
        ("waitlist","Waitlisted for a program"),
        ("interview","Teacher-interviewed for a program"),
        ("teacher_training","Attended teacher-training for a program"),
        ("teacher_checked_in", "Teacher checked in for teaching on the day of the program"),
        ("twophase_reg_done", "Completed two-phase registration"),
    )

    event = models.CharField(max_length=80,choices=EVENT_CHOICES)
    program = models.ForeignKey("program.Program",blank=True,null=True)
    user = AjaxForeignKey(ESPUser, 'id', blank=True, null=True)

    time = models.DateTimeField(blank=True, default = datetime.now)

    class Meta:
        app_label = 'users'

    @classmethod
    def user_completed(cls, user, event, program=None, when=None, only_today=False):
        """
        Returns True if the user is considered to have completed the event.

        Accepts the same parameters as filter().
        """
        return cls.filter(user, event, program, when, only_today).count()>0

    @classmethod
    def filter(cls, user, event, program=None, when=None, only_today=False):
        """
        Returns a QuerySet for all of a user's Records for a particular event,
        under various constraints.

        Parameters:
          user (ESPUser):              The user.
          event (unicode):             The event name.
          program (Program, optional): The program associated with the event.
                                       Use None for events with no associated program.
          when (datetime, optional):   Only Records from before then are considered.
                                       Defaults to datetime.now().
          only_today (bool, optional): If True, only Records from the same day as
                                       'when' are considered.
                                       Defaults to False.
        """
        if when is None:
            when = datetime.now()
        filter = cls.objects.filter(user=user, event=event, time__lte=when)
        if program is not None:
            filter = filter.filter(program=program)
        if only_today:
            filter = filter.filter(time__year=when.year,
                                   time__month=when.month,
                                   time__day=when.day)
        return filter.distinct()

    @classmethod
    def createBit(cls, extension, program, user):
        from esp.accounting.controllers import IndividualAccountingController
        if extension == 'Paid':
            IndividualAccountingController.updatePaid(True, program, user)

        if cls.user_completed(user, extension.lower(), program):
            return False
        else:
            cls.objects.create(
                user = user,
                event = extension.lower(),
                program = program
            )
            return True

    def __unicode__(self):
        return unicode(self.user) + " has completed " + self.event + " for " + unicode(self.program)

#helper method for designing implications
def flatten(choices):
    l=[]
    for x in choices:
        if not isinstance(x[1], tuple): l.append(x[0])
        else: l=l+flatten(x[1])
    return l

class Permission(ExpirableModel):

    #a permission can be assigned to a user, or a role
    user = AjaxForeignKey(ESPUser, blank=True, null=True,
                          help_text="Blank does NOT mean apply to everyone, use role-based permissions for that.")
    role = models.ForeignKey("auth.Group", blank=True, null=True,
                             help_text="Apply this permission to an entire user role (can be blank).")

    #For now, we'll use plain text for a description of what permission it is
    PERMISSION_CHOICES = (
        ("Administer", "Full administrative permissions"),
        ("View", "Able to view a program"),
        ("Onsite", "Access to onsite interfaces"),
        # The following are outside of "Student/" so that they aren't
        # implied by "Student/All".
        ("GradeOverride", "Ignore grade ranges for studentreg"),
        ("OverrideFull", "Register for a full program"),
        ("OverridePhaseZero", "Bypass Phase Zero to proceed to other student reg modules"),
        ("Student Deadlines", (
            ("Student", "Basic student access"),
            ("Student/All", "All student deadlines"),
            ("Student/Acknowledgement", "Student acknowledgement"),
            ("Student/Applications", "Apply for classes"),
            ("Student/Classes", "Register for classes"),
            ("Student/Classes/Lunch", "Register for lunch"),
            ("Student/Classes/Lottery", "Enter the lottery"),
            ("Student/Classes/PhaseZero", "Enter Phase Zero"),
            ("Student/Classes/Lottery/View", "View lottery results"),
            ("Student/ExtraCosts", "Extra costs page"),
            ("Student/MainPage", "Registration mainpage"),
            ("Student/Confirm", "Confirm registration"),
            ("Student/Cancel", "Cancel registration"),
            ("Student/Removal", "Remove class registrations after registration closes"),
            ("Student/Payment", "Pay for a program"),
            ("Student/Profile", "Set profile info"),
            ("Student/Survey", "Access to survey"),
            ("Student/FormstackMedliab", "Access to Formstack medical and liability form"),
            ("Student/Finaid", "Access to financial aid application"),
            ("Student/Webapp", "Access to student onsite webapp"),
        )),
        ("Teacher Deadlines", (
            ("Teacher", "Basic teacher access"),
            ("Teacher/All", "All teacher deadlines"),
            ("Teacher/Acknowledgement", "Teacher acknowledgement"),
            ("Teacher/AppReview", "Review students' apps"),
            ("Teacher/Availability", "Set availability"),
            ("Teacher/Catalog", "Catalog"),
            ("Teacher/Classes", "Classes"),
            ("Teacher/Classes/All", "Classes/All"),
            ("Teacher/Classes/View", "Classes/View"),
            ("Teacher/Classes/Edit", "Classes/Edit"),
            ("Teacher/Classes/CancelReq", "Request class cancellation"),
            ("Teacher/Classes/Coteachers", "Add or remove coteachers"),
            ("Teacher/Classes/Create", "Create classes of all types"),
            ("Teacher/Classes/Create/Class", "Create standard classes"),
            ("Teacher/Classes/Create/OpenClass", "Create open classes"),
            ("Teacher/Events", "Teacher training signup"),
            ("Teacher/Quiz", "Teacher quiz"),
            ("Teacher/MainPage", "Registration mainpage"),
            ("Teacher/Survey", "Teacher Survey"),
            ("Teacher/Profile", "Set profile info"),
            ("Teacher/Survey", "Access to survey"),
            ("Teacher/Webapp", "Access to teacher onsite webapp"),
        )),
        ("Volunteer Deadlines", (
            ("Volunteer", "Basic volunteer access"),
            ("Volunteer/Signup", "Volunteer signup"),
        )),
    )

    PERMISSION_CHOICES_FLAT = flatten(PERMISSION_CHOICES)

    permission_type = models.CharField(max_length=80, choices=PERMISSION_CHOICES)


    implications = {
        "Administer": PERMISSION_CHOICES_FLAT,
        "Student/All": [x for x in PERMISSION_CHOICES_FLAT
                          if x.startswith("Student")],
        "Teacher/All": [x for x in PERMISSION_CHOICES_FLAT
                          if x.startswith("Teacher")],
        "Teacher/Classes/All": [x for x in PERMISSION_CHOICES_FLAT
                                  if x.startswith("Teacher/Classes")],
        "Teacher/Classes/Create": [x for x in PERMISSION_CHOICES_FLAT
                                     if x.startswith("Teacher/Classes/Create")],
    }
    #i'm not really sure if implications is a good idea
    #use sparingly

    #optionally, a permission may be tied to a program
    program = models.ForeignKey("program.Program", blank=True, null=True)
    #note that the ability to do things will not always be determined by
    #a permission object, such as teachers automatically having access to
    #their classes
    #it may, however, be the case that this model is not general enough,
    #in which case program may need to be replaced by a generic foreignkey

    class Meta:
        app_label = 'users'

    @classmethod
    def null_user_has_perm(cls, permission_type, program):
        return cls.valid_objects().filter(permission_type=permission_type,
                program=program, user__isnull=True).exists()

    @classmethod
    def q_permissions_on_program(cls, perm_q, name, program=None, when=None, program_is_none_implies_all=False):
        """
        Build a QuerySet of permissions that would grant a permission.

        Given a Q object on Permission, a permission type, and a program,
        return a QuerySet of permissions satisfying the Q object constraint
        that would grant the permission on the program.
        """
        # As explained above, some Permissions have no specified Program; for
        # some types these are global across all programs, but for most they
        # are not:
        if name in cls.deadline_types:
            program_is_none_implies_all = False

        perms = [name]
        for k,v in cls.implications.items():
            # k implies v: it's a parent permission that includes v
            if name in v: perms.append(k)
        # perms is the list of all permission types that might imply the
        # requested permission

        qprogram = Q(program=program)
        if program_is_none_implies_all:
            qprogram |= Q(program=None)
        initial_qset = cls.objects.filter(perm_q & qprogram).filter(permission_type__in=perms)
        return initial_qset.filter(cls.is_valid_qobject(when=when))

    @classmethod
    def user_has_perm(cls, user, name, program=None, when=None, program_is_none_implies_all=False):
        """Determine if the user has the specified permission on the program.

        :param user:
            Check the permissions assigned to this user.
        :type user:
            `ESPUser`
        :param name:
            The unique identifier of the permission identifier to check for.
            Must be in PERMISSION_CHOICES_FLAT.
        :type name:
            `str`
        :param program:
            Check for permission for `name` on this program.
            If program is None, check only for Permission objects with
            program=None.
            If program_is_none_implies_all is False, check only for Permission
            objects with program=program.
            If program_is_none_implies_all is True, check for Permission
            objects with program=program or program=None.
        :type program:
            `Program` or None
        :param when:
            Check permissions as of this point in time.
            If None, default to datetime.datetime.now().
        :type when:
            `datetime.datetime` or None
        :param program_is_none_implies_all:
            If True, treat Permission objects with program=None as if they are
            global across all programs. Return True if the user has a
            Permission object with program=program or with program=None.
            If False, do not treat Permission objects with program=None as if
            they are global across all programs. Only return True if the user
            has a Permission object with program=program.
            The default behavior is that permissions are not globally
            applicable. Only special permissions that are not in
            deadline_types, like Administer and Onsite, can be granted
            globally on all programs. When checking for these special
            permissions, callers should pass True for this param.
            If name is in deadline_types, set this param to False,
            regardless of the original value.
        :type program_is_none_implies_all:
            `bool`
        :return:
            True if the user has the specified permission, else False.
        :rtype:
            `bool`
        """
        if user.isAdministrator(program=program):
            return True

        quser = Q(user=user) | Q(user=None, role__in=user.groups.all())
        return cls.q_permissions_on_program(quser, name, program, when,
                program_is_none_implies_all).exists()

    @classmethod
    def list_roles_with_perm(cls, name, program):
        """Given a permission type on a program, list roles that would give the
        permission on the program.

        :param name:
            The unique identifier of the permission identifier to check for.
            Must be in PERMISSION_CHOICES_FLAT.
        :type name:
            `str`
        :param program:
            Check for permission for `name` on this program.
        :type program:
            `Program`
        :return:
            List of role names that would give the specified permission.
        :rtype:
            `list` of `str`
        """

        qrole = Q(user=None, role__isnull=False)
        return list(cls.q_permissions_on_program(
                qrole, name, program).values_list('role__name', flat=True))

    #list of all the permission types which are deadlines
    deadline_types = [x for x in PERMISSION_CHOICES_FLAT if x.startswith("Teacher") or x.startswith("Student") or x.startswith("Volunteer")]

    @classmethod
    def deadlines(cls):
        return cls.objects.filter(permission_type__in = cls.deadline_types)

    def recursive(self):
        return bool(self.implications.get(self.permission_type, None))

    def __unicode__(self):
        #TODO
        if self.user is not None:
            user = self.user.username
        else:
            user = self.role

        if self.program is not None:
            program = self.program.niceName()
        else:
            program = "None"

        return "GRANT %s ON %s TO %s" % (self.permission_type,
                                         program, user)

    @classmethod
    def nice_name_lookup(cls,perm_type):
        def squash(choices):
            l=[]
            for x in choices:
                if not isinstance(x[1], tuple): l.append(x)
                else: l=l+squash(x[1])
            return l

        for x in squash(cls.PERMISSION_CHOICES):
            if x[0] == perm_type: return x[1]

    def nice_name(self):
        def squash(choices):
            l=[]
            for x in choices:
                if not isinstance(x[1], tuple): l.append(x)
                else: l=l+squash(x[1])
            return l

        for x in squash(self.PERMISSION_CHOICES):
            if x[0] == self.permission_type: return x[1]

    @classmethod
    def program_by_perm(cls,user,perm):
        """Find all program that user has perm"""
        implies = [perm]
        implies+=[x for x,y in cls.implications.items() if perm in y]

        #Check for global permissions (should only work for non-deadlines and admins)
        if any([cls.user_has_perm(user, x) for x in implies]):
            return Program.objects.all()

        direct = Program.objects.filter(nest_Q(Permission.is_valid_qobject(), 'permission'),
                                       permission__user=user,
                                       permission__permission_type__in=implies)
        role = Program.objects.filter(nest_Q(Permission.is_valid_qobject(), 'permission'),
                                      permission__permission_type__in=implies,
                                      permission__user__isnull=True,
                                      permission__role__in=user.groups.all())
        return direct | role

    @staticmethod
    def user_can_edit_qsd(user,url):
        #the logic here is as follows:
        #  -you must be logged in to edit qsd
        #  -admins can edit any qsd
        #  -admins of a program can edit qsd of the form
        #      /section/<Program.url>/<any url>.html
        #  -teachers of a class with emailcode x (eg x=T1993) can edit
        #      /section/<Program.url>/Classes/<x>/<any url>.html
        if url.endswith(".html"):
            url = url[-5]
        if user is None:
            return False
        if user.isAdmin():
            return True
        import re
        m = re.match("^([^/]*)/([^/]*)/([^/]*)/(.*)",url)
        if m:
            (section, prog1, prog2, rest) = m.groups()
            prog_url = prog1 + "/" + prog2
            try:
                prog = Program.objects.get(url=prog_url)
            except Program.DoesNotExist:
                #not actually a program
                return False
            if user.isAdmin(prog): return True
            m2 = re.match("Classes/(.)(\d+)/(.*)", rest)
            if m2:
                (code, cls_id, basename) = m2.groups()
                try:
                    cls = ClassSubject.objects.get(category__symbol=code,
                                                   id=cls_id)
                except ClassSubject.DoesNotExist:
                    return False
                if user in cls.get_teachers(): return True

        return False

def install_groups(additional_names=None):
    """
    Installs the initial Groups.
    """
    if additional_names is None:
        additional_names = []
    for user_type in (list(ESPUser.getTypes()) + ["StudentRep", "Administrator"] + additional_names):
        Group.objects.get_or_create(name=user_type)

def install():
    """
    Installs some initial users and permissions.
    """
    logger.info("Installing esp.users initial data...")
    install_groups()
    if ESPUser.objects.count() == 1: # We just did a syncdb;
                                     # the one account is the admin account
        user = ESPUser.objects.all()[0]
        user.makeAdmin()

    #   Ensure that there is an onsite user
    if not ESPUser.onsite_user():
        ESPUser.objects.create(username='onsite', first_name='Onsite', last_name='User')
        logger.info('Created onsite user, please set their password in the admin interface.')

#   This import is placed down here since we need it in GradeChangeRequest
#   but esp.dbmail.models imports ESPUser.
from esp.dbmail.models import send_mail

class GradeChangeRequest(TimeStampedModel):
    """
        A grade change request is issued by a student when it is felt
        that the current grade is incorrect.
    """

    claimed_grade = models.PositiveIntegerField()
    grade_before_request = models.PositiveIntegerField()
    reason = models.TextField()
    approved = models.NullBooleanField()
    acknowledged_time = models.DateTimeField(blank=True, null=True)

    requesting_student = models.ForeignKey(ESPUser, related_name='requesting_student_set')
    acknowledged_by = models.ForeignKey(ESPUser, blank=True, null=True)

    class Meta:
        ordering = ['-acknowledged_time','-created']

    def __init__(self, *args, **kwargs):
        super(GradeChangeRequest, self).__init__(*args, **kwargs)
        grade_options = ESPUser.grade_options()

        self._meta.get_field('claimed_grade').choices = zip(grade_options, grade_options)

    def save(self, **kwargs):
        is_new = self.id is None
        super(GradeChangeRequest, self).save(**kwargs)

        if is_new:
            self.send_request_email()
            return

        if self.approved is not None and not self.acknowledged_time:
            self.acknowledged_time = datetime.now()
            self.send_confirmation_email()

        #   Update the student's grade if the request has been approved
        if self.approved is True:
            self.requesting_student.set_grade(self.claimed_grade)

    def _request_email_content(self):
        """
        Returns the email content for the grade change request email.
        """
        context = {'student': self.requesting_student,
                    'change_request':self,
                    'site': Site.objects.get_current()}

        subject = render_to_string('users/emails/grade_change_request_email_subject.txt',
                                   context)
        subject = ''.join(subject.splitlines())

        message = render_to_string('users/emails/grade_change_request_email_message.txt',
                                   context)
        return subject, message

    def send_request_email(self):
        """ Sends the the email for the change request to the LU admin email address"""
        subject, message = self._request_email_content()
        send_mail(subject,
                  message,
                  settings.SERVER_EMAIL,
                  [settings.DEFAULT_EMAIL_ADDRESSES['default'], ])

    def _confirmation_email_content(self):
        context = {'student': self.requesting_student,
                    'change_request':self,
                  'site': Site.objects.get_current(),
                  'settings': settings}

        subject = render_to_string('users/emails/grade_change_confirmation_email_subject.txt',
                                   context)
        subject = ''.join(subject.splitlines())

        message = render_to_string('users/emails/grade_change_confirmation_email_message.txt',
                                   context)
        return subject, message

    def send_confirmation_email(self):
        """
        Sends a confirmation email to the requesting student.
        This email is sent when the administrator confirms a change grade change request.
        """
        subject, message = self._confirmation_email_content()
        send_mail(subject,
                  message,
                  settings.DEFAULT_FROM_EMAIL,
                  [self.requesting_student.email, ])

    def get_admin_url(self):
        return urlresolvers.reverse("admin:%s_%s_change" %
        (self._meta.app_label, self._meta.model_name), args=(self.id,))


    def __unicode__(self):
        return  "%s requests a grade change to %s" % (self.requesting_student, self.claimed_grade) + (" (Approved)" if self.approved else "")

# We can't import these earlier because of circular stuff...
from esp.users.models.forwarder import UserForwarder # Don't delete, needed for app loading
from esp.cal.models import Event
from esp.program.models import ClassSubject, ClassSection, Program, StudentRegistration
from esp.resources.models import Resource
