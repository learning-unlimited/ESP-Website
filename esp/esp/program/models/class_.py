__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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

import datetime
from datetime import timedelta
import time
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)

import random

# django Util
from django.conf import settings
from django.db import models
from django.db.models.query import Q
from django.db.models import signals, Sum
from django.db.models.manager import Manager
from collections import OrderedDict
from django.template.loader import render_to_string
from django.template import Template, Context
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

from django_extensions.db.fields.json import JSONField

# ESP Util
from esp.db.fields import AjaxForeignKey
from esp.utils.property import PropertyDict
from esp.utils.query_utils import nest_Q
from esp.tagdict.models import Tag
from esp.mailman import add_list_member, remove_list_member

# ESP models
from esp.cal.models import Event
from esp.dbmail.models import send_mail
from esp.qsd.models import QuasiStaticData
from esp.qsdmedia.models import Media
from esp.users.models import ESPUser, Permission, PersistentQueryFilter
from esp.program.models import Program
from esp.program.models import StudentRegistration, StudentSubjectInterest, RegistrationType
from esp.program.models import ScheduleMap, ScheduleConstraint
from esp.program.models import ArchiveClass
from esp.resources.models         import Resource, ResourceRequest, ResourceAssignment, ResourceType
from argcache                     import cache_function, wildcard
from argcache.extras.derivedfield import DerivedField

from esp.middleware.threadlocalrequest import get_current_request

from esp.customforms.linkfields import CustomFormsLinkModel

__all__ = ['ClassSection', 'ClassSubject', 'ClassManager', 'ClassCategories', 'ClassSizeRange']

CANCELLED = -20
REJECTED = -10
UNREVIEWED = 0
HIDDEN = 5
ACCEPTED = 10

STATUS_CHOICES = (
        (CANCELLED, "cancelled"),
        (REJECTED, "rejected"),
        (UNREVIEWED, "unreviewed"),
        (HIDDEN, "accepted but hidden"),
        (ACCEPTED, "accepted"),
        )

STATUS_CHOICES_DICT = dict(STATUS_CHOICES)

OPEN = 0
CLOSED = 10

REGISTRATION_CHOICES = (
            (OPEN, "open"),
            (CLOSED, "closed"),
            )



class ClassSizeRange(models.Model):
    range_min = models.IntegerField(null=False)
    range_max = models.IntegerField(null=False)
    program   = models.ForeignKey(Program, blank=True, null=True)

    @classmethod
    def get_ranges_for_program(cls, prog):
        ranges = cls.objects.filter(program=prog)
        if ranges:
            return ranges
        else:
            for range in cls.objects.filter(program=None):
                k = cls()
                k.range_min = range.range_min
                k.range_max = range.range_max
                k.program = prog
                k.save()
            return cls.objects.filter(program=prog)

    def range_str(self):
        return u"%d-%d" %(self.range_min, self.range_max)

    def __unicode__(self):
        return u"Class Size Range: " + self.range_str()

    class Meta:
        app_label='program'


class ClassManager(Manager):
    def __repr__(self):
        return u"ClassManager()"

    def approved(self, return_q_obj=False):
        if return_q_obj:
            return Q(status = ACCEPTED)

        return self.filter(status = ACCEPTED)

    def catalog(self, program, ts=None, force_all=False, initial_queryset=None, use_cache=True, cache_only=False, order_args_override=None):
        # Try getting the catalog straight from cache
        catalog = self.catalog_cached(program, ts, force_all, initial_queryset, cache_only=True, order_args_override=order_args_override)
        if catalog is None:
            # Get it from the DB, then try prefetching class sizes
            catalog = self.catalog_cached(program, ts, force_all, initial_queryset, use_cache=use_cache, cache_only=cache_only, order_args_override=order_args_override)
        else:
            for cls in catalog:
                for sec in cls.get_sections():
                    if hasattr(sec, '_count_students'):
                        del sec._count_students

        return catalog


    @cache_function
    def catalog_cached(self, program, ts=None, force_all=False, initial_queryset=None, order_args_override=None):
        """ Return a queryset of classes for view in the catalog.

        In addition to just giving you the classes, it also
        queries for the category's title (cls.category_txt)
        and the total # of media.
        """
        now = datetime.datetime.now()

        enrolled_type = RegistrationType.get_map(include=['Enrolled'], category='student')['Enrolled']

        if initial_queryset:
            classes = initial_queryset
        else:
            classes = self.all()

        if not force_all:
            classes = classes.filter(self.approved(return_q_obj=True))

        classes = classes.select_related('category')

        if program != None:
            classes = classes.filter(parent_program = program)

        if ts is not None:
            classes = classes.filter(sections__meeting_times=ts)

        classes = classes.annotate(_num_students=Sum('sections__enrolled_students'))
        classes = classes.prefetch_related('teachers')

        #   Retrieve the content type for finding class documents (generic relation)
        content_type_id = ContentType.objects.get_for_model(ClassSubject).id

        select = OrderedDict([('media_count', 'SELECT COUNT(*) FROM "qsdmedia_media" WHERE ("qsdmedia_media"."owner_id" = "program_class"."id") AND ("qsdmedia_media"."owner_type_id" = %s)'),
                             ('_index_qsd', 'SELECT COUNT(*) FROM "qsd_quasistaticdata" WHERE ("qsd_quasistaticdata"."name" = \'learn:index\' AND "qsd_quasistaticdata"."url" LIKE %s AND "qsd_quasistaticdata"."url" SIMILAR TO %s || "program_class"."id" || %s)'),
                             ('_studentapps_count', 'SELECT COUNT(*) FROM "program_studentappquestion" WHERE ("program_studentappquestion"."subject_id" = "program_class"."id")')])

        select_params = [ content_type_id,
                          '%/Classes/%',
                          '%[A-Z]',
                          '/%',
                         ]
        classes = classes.extra(select=select, select_params=select_params)

        #   Allow customized orderings for the catalog.
        #   These are the default ordering fields in descending order of priority.
        if order_args_override:
            order_args = order_args_override
        else:
            order_args = ['category__symbol', 'category__category', 'sections__meeting_times__start', '_num_students', 'id']
            #   First check if there is an ordering specified for the program.
            program_sort_fields = Tag.getProgramTag('catalog_sort_fields', program)
            if program_sort_fields:
                #   If you found one, use it.
                order_args = program_sort_fields.split(',')

        #   Order the QuerySet using the specified list.
        classes = classes.order_by(*order_args)

        classes = classes.distinct()
        classes = list(classes)

        #   Filter out duplicates by ID.  This is necessary because Django's ORM
        #   adds the related fields (e.g. sections__meeting_times) to the SQL
        #   SELECT statement and doesn't include them in the result.
        #   See http://docs.djangoproject.com/en/dev/ref/models/querysets/#s-distinct
        counter = 0
        index = 0
        max_count = len(classes)
        id_list = []
        while counter < max_count:
            cls = classes[index]
            cls._temp_index = counter
            if cls.id not in id_list:
                id_list.append(cls.id)
                index += 1
            else:
                classes.remove(cls)
            counter += 1

        # All class ID's; used by later query ugliness:
        class_ids = map(lambda x: x.id, classes)

        # Now to get the sections corresponding to these classes...

        sections = ClassSection.objects.filter(parent_class__in=class_ids)

        sections = ClassSection.prefetch_catalog_data(sections.distinct())

        sections_by_parent_id = defaultdict(list)
        for s in sections:
            sections_by_parent_id[s.parent_class_id].append(s)

        # Now, to combine all of the above

        if len(classes) >= 1:
            p = Program.objects.get(id=classes[0].parent_program_id)

        for c in classes:
            c._teachers = list(c.teachers.all())
            c._teachers.sort(cmp=lambda t1, t2: cmp(t1.last_name, t2.last_name))
            c._sections = sections_by_parent_id[c.id]
            for s in c._sections:
                s.parent_class = c
            c._sections.sort(cmp=lambda s1, s2: cmp(s1.id, s2.id))
            c.parent_program = p # So that if we set attributes on one instance of the program,
                                 # they show up for all instances.

        return classes
    catalog_cached.depend_on_model('program.ClassSubject')
    catalog_cached.depend_on_model('program.ClassSection')
    catalog_cached.depend_on_model('qsdmedia.Media')
    catalog_cached.depend_on_model('tagdict.Tag')

    #perhaps make it program-specific?
    @staticmethod
    def is_class_index_qsd(qsd):
        parts = qsd.url.split("/")
        return (parts and len(parts) > 1) and \
            parts[-1] == "index" and \
            parts[0] == "learn" and \
            "Classes" in parts
    catalog_cached.depend_on_row('qsd.QuasiStaticData', lambda page: {},
                                 lambda page: ClassManager.is_class_index_qsd(page))

    def random_class(self, q=None):
        classes = self.filter(self.approved(return_q_obj=True))
        if q is not None: classes = classes.filter(q)
        count = classes.count()
        return classes[random.randint(0, count - 1)]

class ClassSection(models.Model):
    """ An instance of class.  There should be one of these for each weekend of HSSP, for example; or multiple
    parallel sections for a course being taught more than once at Splash or Spark. """

    status = models.IntegerField(choices=STATUS_CHOICES, default=UNREVIEWED)                 #As the choices are shared with ClassSubject, they're at the top of the file
    registration_status = models.IntegerField(choices=REGISTRATION_CHOICES, default=OPEN)    #Ditto.
    duration = models.DecimalField(blank=True, null=True, max_digits=5, decimal_places=2)
    meeting_times = models.ManyToManyField(Event, related_name='meeting_times', blank=True)
    max_class_capacity = models.IntegerField(blank=True, null=True)

    parent_class = AjaxForeignKey('ClassSubject', related_name='sections')

    registrations = models.ManyToManyField(ESPUser, through='StudentRegistration')

    @classmethod
    def ajax_autocomplete(cls, data):
        clsname = data.strip().split(':')
        id_ = clsname[0].split('s')
        sec_index = ''.join(id_[1:])
        id_ = id_[0]

        query_set = cls.objects.filter(parent_class__category__symbol=id_[0],
                                       parent_class__id__startswith=id_[1:])

        if len(clsname) > 1:
            title  = ':'.join(clsname[1:])
            if len(title.strip()) > 0:
                query_set = query_set.filter(parent_class__title__istartswith = title.strip())

        values_set = query_set.order_by('parent_class__category__symbol','id').select_related()
        values = []
        for v in values_set:
            index = str(v.index())
            if (not sec_index) or (sec_index == index):
                values.append({'parent_class__emailcode': v.parent_class.emailcode(),
                               'parent_class__title': v.parent_class.title,
                               'secnum': index,
                               'id': str(v.id)})

        for value in values:
            value['ajax_str'] = '%ss%s: %s' % (value['parent_class__emailcode'], value['secnum'], value['parent_class__title'])
        return values

    @classmethod
    def prefetch_catalog_data(cls, queryset):
        """ Take a queryset of a set of ClassSubject's, and annotate each class in it with the '_count_students' and 'event_ids' fields (used internally when available by many functions to save on queries later) """
        now = datetime.datetime.now()
        enrolled_type = RegistrationType.get_map()['Enrolled']

        select = OrderedDict([( '_count_students', 'SELECT COUNT(DISTINCT "program_studentregistration"."user_id") FROM "program_studentregistration" WHERE ("program_studentregistration"."relationship_id" = %s AND "program_studentregistration"."section_id" = "program_classsection"."id" AND ("program_studentregistration"."start_date" IS NULL OR "program_studentregistration"."start_date" <= %s) AND ("program_studentregistration"."end_date" IS NULL OR "program_studentregistration"."end_date" >= %s))')])

        select_params = [ enrolled_type.id,
                          now,
                          now,
                         ]

        sections = queryset.prefetch_related('meeting_times')
        sections = sections.extra(select=select, select_params=select_params)
        sections = list(sections)

        # Now, to combine all of the above:

        for s in sections:
            s._events = list(s.meeting_times.all())
            s._events.sort(cmp=lambda e1, e2: cmp(e1.start, e2.start))

        return sections

    def get_absolute_url(self):
        return self.parent_class.get_absolute_url()

    def get_edit_absolute_url(self):
        return self.parent_class.get_edit_absolute_url()

    @cache_function
    def get_meeting_times(self):
        return self.meeting_times.all()
    get_meeting_times.depend_on_m2m('program.ClassSection', 'meeting_times', lambda sec, event: {'self': sec})

    #   Some properties for traits that are actually traits of the ClassSubjects.
    def _get_parent_program(self):
        return self.parent_class.parent_program
    parent_program = property(_get_parent_program)

    def _get_teachers(self):
        return self.parent_class.get_teachers()
    teachers = property(_get_teachers)

    def _get_category(self):
        return self.parent_class.category
    category = property(_get_category)

    def _get_room_capacity(self, rooms = None):
        # rooms should be a queryset
        if rooms == None:
            rooms = self.classrooms()

        # Take the summed classroom capacity for each timeblock, then take the minimum of those sums
        rc = min(d.get('capacity', 0) for d in rooms.values('event').order_by('event').annotate(capacity=Sum('num_students')))

        options = self.parent_program.studentclassregmoduleinfo
        if options.apply_multiplier_to_room_cap:
            rc = int(rc * options.class_cap_multiplier + options.class_cap_offset)

        return rc

    @cache_function
    def _get_capacity(self, ignore_changes=False):
        ans = None
        rooms = self.classrooms()
        if self.max_class_capacity is not None:
            ans = self.max_class_capacity
        else:
            if len(rooms) == 0:
                if not ans:
                    ans = self.parent_class.class_size_max
            else:
                ans = min(self.parent_class.class_size_max, self._get_room_capacity(rooms))

        #hacky fix for classes with no max size
        if ans == None or ans == 0:
            # New class size capacity condition set for Splash 2010.  In code
            # because it seems like a fairly reasonable metric.
            if self.parent_class.allowable_class_size_ranges.all() and len(rooms) != 0:
                ans = min(max(self.parent_class.allowable_class_size_ranges.order_by('-range_max').values_list('range_max', flat=True)[0], self.parent_class.class_size_optimal), self._get_room_capacity(rooms))
            elif self.parent_class.class_size_optimal and len(rooms) != 0:
                ans = min(self.parent_class.class_size_optimal, self._get_room_capacity(rooms))
            elif self.parent_class.class_size_optimal:
                ans = self.parent_class.class_size_optimal
            elif len(rooms) != 0:
                ans = self._get_room_capacity(rooms)
            else:
                ans = 0

        options = self.parent_program.studentclassregmoduleinfo

        #   Apply dynamic capacity rule
        if not (ignore_changes or options.apply_multiplier_to_room_cap):
            return int(ans * options.class_cap_multiplier + options.class_cap_offset)
        else:
            return int(ans)

    _get_capacity.depend_on_m2m('program.ClassSection', 'meeting_times', lambda sec, event: {'self': sec})
    _get_capacity.depend_on_row('program.ClassSection', lambda r: {'self': r})
    _get_capacity.depend_on_model('program.ClassSubject')
    _get_capacity.depend_on_model('resources.Resource')
    _get_capacity.depend_on_row('program.ClassSection', 'self')
    _get_capacity.depend_on_row('resources.ResourceRequest', lambda r: {'self': r.target})
    _get_capacity.depend_on_row('resources.ResourceAssignment', lambda r: {'self': r.target})
    _get_capacity.depend_on_model('modules.StudentClassRegModuleInfo')


    capacity = property(_get_capacity)

    def title(self):
        return self.parent_class.title

    def __unicode__(self):
        return u'%s: %s' % (self.emailcode(), self.title())

    def index(self):
        """ Get index of this section among those belonging to the parent class. """
        pc = self.parent_class
        pc_sec_ids = map(lambda x: x.id, pc.get_sections())
        return list(pc_sec_ids).index(self.id) + 1

    def delete(self, adminoverride=False):
        if self.num_students() > 0 and not adminoverride:
            return False

        self.getResourceRequests().delete()
        self.getResourceAssignments().delete()
        self.meeting_times.clear()

        super(ClassSection, self).delete()

    def getResourceAssignments(self):
        return self.resourceassignment_set.all()

    def getResources(self):
        assignment_list = self.getResourceAssignments()
        return [a.resource for a in assignment_list]

    def getResourceRequests(self):
        return ResourceRequest.objects.filter(target=self)

    def clearResourceRequests(self):
        for rr in self.getResourceRequests():
            rr.delete()

    def classroomassignments(self):
        return self.getResourceAssignments().filter(target=self, resource__res_type__name="Classroom")

    def resourceassignments(self):
        """   Get all assignments pertaining to floating resources like projectors. """

        cls_restype = ResourceType.get_or_create('Classroom')
        ta_restype = ResourceType.get_or_create('Teacher Availability')
        return self.getResourceAssignments().filter(target=self).exclude(resource__res_type=cls_restype).exclude(resource__res_type=ta_restype)

    def classrooms(self):
        """ Returns the list of classroom resources assigned to this class."""

        ra_list = self.classroomassignments().values_list('resource', flat=True)
        return Resource.objects.filter(id__in=ra_list)

    def initial_rooms(self):
        meeting_times = self.get_meeting_times()
        if len(meeting_times) > 0:
            initial_time = min(meeting_times, key=lambda event: event.start)
            return self.classrooms().filter(event=initial_time).order_by('id')
        else:
            return Resource.objects.none()

    def prettyrooms(self):
        """ Return the pretty name of the rooms. """
        if self.meeting_times.count() > 0:
            return [x.name for x in self.initial_rooms()]
        else:
            return []

    def emailcode(self):
        return self.parent_class.emailcode() + u's' + unicode(self.index())

    def already_passed(self):
        start_time = self.start_time()
        if start_time is None:
            return True
        time_passed = datetime.datetime.now() - start_time.start
        if self.parent_class.allow_lateness:
            if time_passed > timedelta(0, 1200):
                return True
        else:
            if time_passed > timedelta(0):
                return True
        return False

    def start_time_prefetchable(self):
        """Like self.start_time().start, but can be prefetched.

        Gets the start time of a class.  If self.meeting_times.all() has been
        prefetched, this will not hit the DB.  If it has not been prefetched,
        this will not help.
        """
        mts = self.meeting_times.all()
        if mts:
            return min(mt.start for mt in mts)
        else:
            return None

    def start_time(self):
        if self.meeting_times.count() > 0:
            return self.meeting_times.order_by('start')[0]
        else:
            return None

    def pretty_start_time(self):
        s = self.start_time()
        if s:
            return s.short_time()
        else:
            return u'N/A'

    #   Scheduling helper functions

    @cache_function
    def sufficient_length(self, event_list=None):
        """   This function tells if the class' assigned times are sufficient to cover the duration.
        If the duration is not set, 1 hour is assumed. """

        duration = self.duration or 1.0

        if event_list is None:
            event_list = list(self.meeting_times.all().order_by('start'))
        if Event.total_length(event_list).total_seconds() < duration * 3600:
            return False
        else:
            return True
    sufficient_length.depend_on_m2m('program.ClassSection', 'meeting_times', lambda sec, event: {'self': sec})


    def extend_timeblock(self, event, merged=True):
        """ Return the Event list or (merged Event) for this class's duration if the class starts in the
        provided timeslot and continues contiguously until its duration has ended. """

        event_list = [event]
        all_events = list(self.parent_program.getTimeSlots())
        event_index = all_events.index(event)

        while not self.sufficient_length(event_list):
            event_index += 1
            event_list.append(all_events[event_index])

        if merged:
            return Event.collapse(event_list, tol=datetime.timedelta(minutes=10))
        else:
            return event_list

    @cache_function
    def scheduling_status(self):
        #   Return a little string that tells you what's up with the resource assignments.
        if not self.sufficient_length():
            retVal = 'Needs time'
        elif self.classrooms().count() < 1:
            retVal = 'Needs room'
        elif self.unsatisfied_requests().count() > 0:
            retVal = 'Needs resources'
        else:
            retVal = 'Happy'
        return retVal
    scheduling_status.depend_on_row('program.ClassSection', lambda cs: {'self': cs})
    scheduling_status.depend_on_m2m('program.ClassSection', 'meeting_times', lambda cs, ev: {'self': cs})
    scheduling_status.depend_on_row('resources.ResourceRequest', lambda rr: {'self': rr.target})
    scheduling_status.depend_on_row('resources.ResourceAssignment', lambda ra: {'self': ra.target})

    @cache_function
    def unsatisfied_requests(self):
        if self.classrooms().count() > 0:
            primary_room = self.classrooms()[0]
            result = primary_room.satisfies_requests(self)[1]
        else:
            result = self.getResourceRequests()
        return result
    unsatisfied_requests.depend_on_cache(scheduling_status, lambda cs=wildcard, **kwargs: {'self': cs})

    def assign_meeting_times(self, event_list):
        self.meeting_times.clear()
        for event in set(event_list):
            self.meeting_times.add(event)

    def clear_meeting_times(self):
        self.meeting_times.clear()

    def assign_start_time(self, first_event):
        """ Get enough events following the first one until you have the class duration covered.
        Then add them. """

        #   This means we have to clear the classrooms.
        #   But we will try to re-assign the same room at the new times if it is available.
        current_rooms = self.initial_rooms()

        self.clearRooms()
        self.clearFloatingResources()

        event_list = self.extend_timeblock(first_event, merged=False)
        self.assign_meeting_times(event_list)

        #   Check to see if the desired rooms are available at the new times
        availability = True
        for e in event_list:
            for room in current_rooms:
                if not room.is_available(e):
                    availability = False

        #   If the desired rooms are available, assign them.  (If not, no big deal.)
        if availability:
            for room in current_rooms:
                self.assign_room(room)

    def end_time(self):
        """Returns the meeting time for this section with the latest end time"""
        all_times = self.meeting_times.order_by("-end")
        if all_times:
            return all_times[0]
        else:
            return None

    def end_time_prefetchable(self):
        """Like self.end_time().end, but can be prefetched.

        See self.start_time_prefetchable().
        """
        mts = self.meeting_times.all()
        if mts:
            return max(mt.end for mt in mts)
        else:
            return None

    def assign_room(self, base_room, clear_others=False, allow_partial=False, lock=0):
        """ Assign the classroom given, at the times needed by this class. """
        rooms_to_assign = base_room.identical_resources().filter(event__in=list(self.meeting_times.all()))

        status = True
        errors = []

        if clear_others:
            self.clearRooms()

        if rooms_to_assign.count() != self.meeting_times.count():
            status = False
            errors.append( u'Room %s does not exist at the times requested by %s.' % (base_room.name, self.emailcode()) )
            if not allow_partial:
                return (status, errors)

        for i, r in enumerate(rooms_to_assign):
            result = self.assignClassRoom(r, lock)
            if not result:
                status = False
                occupiers_str = ''
                occupiers_set = r.assignments()
                if occupiers_set.count() > 0: # We really shouldn't have to test for this, but I guess it's safer not to assume... -ageng 2008-11-02
                    occupiers_str = u' by %s during %s' % ((occupiers_set[0].target or occupiers_set[0].target_subj).emailcode(), r.event.pretty_time())
                errors.append( u'Room %s is occupied%s.' % ( base_room.name, occupiers_str ) )
                # If we don't allow partial fulfillment, undo and quit.
                if not allow_partial:
                    for r2 in rooms_to_assign[:i]:
                        r2.clear_assignments()
                    break

        return (status, errors)

    def viable_times(self, ignore_classes=False):
        """ Return a list of Events for which all of the teachers are available. """

        def intersect_lists(list_of_lists):
            if len(list_of_lists) == 0:
                return []

            base_list = list_of_lists[0]
            for other_list in list_of_lists[1:]:
                i = 0
                for elt in base_list:
                    if elt not in other_list:
                        base_list.remove(elt)
            return base_list

        teachers = self.parent_class.get_teachers()

        timeslot_list = []
        for t in teachers:
            timeslot_list.append(list(t.getAvailableTimes(self.parent_program, ignore_classes)))

        available_times = intersect_lists(timeslot_list)

        #   If the class is already scheduled, put its time in.
        if self.meeting_times.count() > 0:
            for k in self.meeting_times.all():
                if k not in available_times:
                    available_times.append(k)

        timeslots = Event.group_contiguous(available_times)

        viable_list = []

        for timegroup in timeslots:
            for i in range(0, len(timegroup)):
                #   Check whether there is enough time remaining in the block.
                if self.sufficient_length(timegroup[i:len(timegroup)]):
                    viable_list.append(timegroup[i])

        return viable_list

    @cache_function
    def viable_rooms(self):
        """ Returns a list of Resources (classroom type) that satisfy all of this class's resource requests.
        Resources matching the first time block of the class will be returned. """

        def room_satisfies_times(room, times):
            room_times = room.matching_times()
            satisfaction = True
            for t in times:
                if t not in room_times:
                    satisfaction = False
            return satisfaction

        #   This function is only meaningful if the times have already been set.  So, back out if they haven't.
        if not self.sufficient_length():
            return []

        #   Start with all rooms the program has.
        #   Filter the ones that are available at all times needed by the class.
        filter_qs = []
        ordered_times = self.meeting_times.order_by('start')
        first_time = ordered_times[0]
        possible_rooms = self.parent_program.getAvailableClassrooms(first_time)

        viable_list = filter(lambda x: room_satisfies_times(x, ordered_times), possible_rooms)

        return viable_list

    viable_rooms.depend_on_row('program.ClassSection', lambda cs: {'self': cs})
    viable_rooms.depend_on_m2m('program.ClassSection', 'meeting_times', lambda cs, ev: {'self': cs})
    viable_rooms.depend_on_model('resources.Resource')

    def clearRooms(self):
        self.classroomassignments().delete()

    def clearFloatingResources(self):
        self.resourceassignments().delete()

    def assignClassRoom(self, classroom, lock_level=0):
        #   Assign an individual resource to this class.
        if classroom.is_taken():
            return False
        else:
            new_assignment = ResourceAssignment()
            new_assignment.resource = classroom
            new_assignment.target = self
            new_assignment.lock_level = lock_level
            new_assignment.save()
            return True

    """ These two functions make it easier to set whether a section is fair game
        for adjustment by automatic scheduling. """

    def lock_schedule(self, lock_level=1):
        self.resourceassignment_set.all().update(lock_level=lock_level)

    def unlock_schedule(self, lock_level=0):
        self.resourceassignment_set.all().update(lock_level=lock_level)


    @cache_function
    def timeslot_ids(self):
        return self.meeting_times.all().values_list('id', flat=True)
    timeslot_ids.depend_on_m2m('program.ClassSection', 'meeting_times', lambda instance, object: {'self': instance})

    def cannotRemove(self, user):
        relevantConstraints = self.parent_program.getScheduleConstraints()
        if relevantConstraints:
            sm = ScheduleMap(user, self.parent_program)
            sm.remove_section(self)
            for exp in relevantConstraints:
                if not exp.evaluate(sm, recursive=False):
                    return u"You can't remove this class from your schedule because it would violate the requirement that you %s.  You can go back and correct this." % exp.requirement.label
        return False

    def cannotAdd(self, user, checkFull=True, autocorrect_constraints=True, ignore_constraints=False, webapp=False):
        """ Go through and give an error message if this user cannot add this section to their schedule. """

        # Check if section is full
        if checkFull and self.isFull(webapp=webapp):
            scrmi = self.parent_class.parent_program.studentclassregmoduleinfo
            return scrmi.temporarily_full_text

        # Test any scheduling constraints
        if ignore_constraints:
            relevantConstraints = ScheduleConstraint.objects.none()
        else:
            relevantConstraints = self.parent_program.getScheduleConstraints()

        if relevantConstraints:
            # Set up a ScheduleMap; fake-insert this class into it
            sm = ScheduleMap(user, self.parent_program)
            sm.add_section(self)

            for exp in relevantConstraints:
                if not exp.evaluate(sm, recursive=autocorrect_constraints):
                    return u"Adding <i>%s</i> to your schedule requires that you %s.  You can go back and correct this." % (self.title(), exp.requirement.label)

        scrmi = self.parent_program.studentclassregmoduleinfo
        section_list = user.getEnrolledSectionsFromProgram(self.parent_program)

        # check to see if there's a conflict:
        my_timeslots = self.timeslot_ids()
        for sec in section_list:
            if sec.parent_class == self.parent_class:
                return u'You are already signed up for a section of this class!'
            if hasattr(sec, '_timeslot_ids'):
                timeslot_ids = sec._timeslot_ids
            else:
                timeslot_ids = sec.timeslot_ids()
            for tid in timeslot_ids:
                if tid in my_timeslots:
                    if self.parent_class.sections.filter(resourceassignment__isnull=False, meeting_times__isnull=False, status=10).exclude(id=self.id):
                        return u'This section conflicts with your schedule--check out the other sections!'
                    else:
                        return u'This class conflicts with your schedule!'

        # check to see if registration has been closed for this section
        if not self.isRegOpen():
            return u'Registration for this section is not currently open.'

        # check to see if the section has been cancelled
        if self.isCancelled():
            return u'This section has been cancelled.'

        # check to make sure they haven't already registered for too many classes in this section
        if scrmi.use_priority:
            priority = user.getRegistrationPriority(self.parent_class.parent_program, self.meeting_times.all())
            if priority > scrmi.priority_limit:
                return u'You are only allowed to select up to %s top classes' % (scrmi.priority_limit)

        # this user *can* add this class!
        return False

    def conflicts(self, teacher, meeting_times=None):
        """Return a scheduling conflict if one exists, or None."""
        user = teacher
        if meeting_times is None:
            meeting_times = self.meeting_times.all()
        for sec in user.getTaughtSections(self.parent_program).exclude(id=self.id):
            for time in sec.meeting_times.all():
                if meeting_times.filter(id = time.id).count() > 0:
                    return (sec, time)

        return None

    def cannotSchedule(self, meeting_times, ignore_classes=True):
        """
        Returns False if the given times work; otherwise, an error message.

        Assumes meeting_times is a sorted QuerySet of correct length.

        """
        # check if proposed times are the same as the current meeting_times
        current_times = self.meeting_times.all()
        if all(time in current_times for time in meeting_times):
            return False
        # otherwise, check if all teachers are available
        for t in self.teachers:
            available = t.getAvailableTimes(self.parent_program, ignore_classes=ignore_classes)
            for e in meeting_times:
                if e not in available:
                    return u"The teacher %s has not indicated availability during %s." % (t.name(), e.pretty_time())
            conflicts = self.conflicts(t, meeting_times)
            if conflicts:
                return u"The teacher %s is teaching %s during %s." % (t.name(), conflicts[0].emailcode(), conflicts[1].pretty_time())
            # Fallback in case we couldn't come up with details
        return False

    #   If the values returned by this function are ever needed in QuerySet form,
    #   something will need to be changed.
    @cache_function
    def students_dict(self):
        """
        Returns a dict of RegistrationType objects to a list of Student objects associated with
        this class and that registration type.  e.g.:
        {RegistrationType(name='Enrolled'): [student1, student2, student3],
         ...
        }
        """
        now = datetime.datetime.now()

        rmap = RegistrationType.get_map()
        result = {}
        for key in rmap:
            result_key = rmap[key] #the RegistrationType object, not the name field
            result[result_key] = list(self.registrations.filter(nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration'), studentregistration__relationship=rmap[key]).distinct())
            if len(result[result_key]) == 0:
                del result[result_key]
        return result
    students_dict.depend_on_row('program.StudentRegistration', lambda reg: {'self': reg.section})

    def students_prereg(self):
        return self.registrations.filter(nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration')).distinct()

    def students(self, verbs=['Enrolled']):
        result = ESPUser.objects.none()
        for verb_str in verbs:
            result = result | self.registrations.filter(nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration'), studentregistration__relationship__name=verb_str)
        return result.distinct()

    def students_checked_in(self):
        return self.students() & self.parent_program.currentlyCheckedInStudents()

    @cache_function
    def num_students_checked_in(self):
        return self.students_checked_in().count()
    num_students_checked_in.depend_on_model('users.Record')
    num_students_checked_in.depend_on_row('program.StudentRegistration', lambda reg: {'self': reg.section})

    @cache_function
    def count_ever_checked_in_students(self):
        return (self.students() & ESPUser.objects.filter(Q(record__event="attended", record__program=self.parent_program)).distinct()).count()
    count_ever_checked_in_students.depend_on_model('users.Record')
    count_ever_checked_in_students.depend_on_row('program.StudentRegistration', lambda reg: {'self': reg.section})

    ever_checked_in_students = DerivedField(models.IntegerField, count_ever_checked_in_students)(null=False, default=0)

    @cache_function
    def num_students_prereg(self):
        return self.students_prereg().count()
    num_students_prereg.depend_on_row('program.StudentRegistration', lambda reg: {'self': reg.section})

    @cache_function
    def num_students(self, verbs=['Enrolled']):
        if verbs == ['Enrolled']:
            if not hasattr(self, '_count_students'):
                self._count_students = self.students(verbs).count()
            return self._count_students
        return self.students(verbs).count()
    num_students.depend_on_row('program.StudentRegistration', lambda reg: {'self': reg.section})

    @cache_function
    def count_enrolled_students(self):
        return self.num_students(use_cache=False)
    count_enrolled_students.depend_on_row('program.StudentRegistration', lambda reg: {'self': reg.section})

    enrolled_students = DerivedField(models.IntegerField, count_enrolled_students)(null=False, default=0)

    @cache_function
    def count_attending_students(self):
        return self.num_students(verbs=['Attended'], use_cache=False)
    count_attending_students.depend_on_row('program.StudentRegistration', lambda reg: {'self': reg.section})

    attending_students = DerivedField(models.IntegerField, count_attending_students)(null=False, default=0)

    def cancel(self, email_students=True, include_lottery_students=False, text_students=False, email_teachers=True, explanation=None, unschedule=False):
        # To avoid circular imports
        from esp.program.modules.handlers.grouptextmodule import GroupTextModule

        if include_lottery_students:
            student_verbs = ['Enrolled', 'Interested', 'Priority/1']
        else:
            student_verbs = ['Enrolled']

        email_ssis = include_lottery_students and all([sec.isCancelled() for sec in self.parent_class.get_sections() if sec!=self])

        context = {'sec': self, 'prog': self.parent_program, 'explanation': explanation}
        context['full_group_name'] = Tag.getTag('full_group_name') or '%s %s' % (settings.INSTITUTION_NAME, settings.ORGANIZATION_SHORT_NAME)
        context['site_url'] = Site.objects.get_current().domain
        context['email_students'] = email_students
        context['num_students'] = self.num_students(student_verbs)
        context['email_ssis'] = email_ssis

        email_title = 'Class Cancellation at %s - Section %s' % (self.parent_program.niceName(), self.emailcode())
        ssi_email_title = 'Class Cancellation at %s - Class %s' % (self.parent_program.niceName(), self.parent_class.emailcode())

        if email_students:
            #   Send email to each student
            students_to_email = {}
            if email_ssis:
                q_ssi = Q(studentsubjectinterest__subject=self.parent_class) & nest_Q(StudentSubjectInterest.is_valid_qobject(), 'studentsubjectinterest')
                ssi_students = ESPUser.objects.filter(q_ssi).exclude(id__in=self.students(student_verbs)).distinct()
                for student in ssi_students:
                    students_to_email[student] = False
            for student in self.students(student_verbs):
                students_to_email[student] = True

            for student in students_to_email:
                to_email = ['%s <%s>' % (student.name(), student.email)]
                from_email = '%s at %s <%s>' % (self.parent_program.program_type, settings.INSTITUTION_NAME, self.parent_program.director_email)
                #   Here we render the template to include the username, and also whether the student is registered
                context['classreg'] = students_to_email[student]
                context['user'] = student
                msgtext = render_to_string('email/class_cancellation.txt', context)
                if students_to_email[student]:
                    send_mail(email_title, msgtext, from_email, to_email)
                else:
                    send_mail(ssi_email_title, msgtext, from_email, to_email)

        if text_students and self.parent_program.hasModule('GroupTextModule') and GroupTextModule.is_configured():
            if self.students(student_verbs).distinct().count() > 0:
                msgtext = render_to_string('texts/class_cancellation.txt', context)
                students_to_text = PersistentQueryFilter.create_from_Q(ESPUser, Q(id__in=[x.id for x in self.students(student_verbs)]))
                GroupTextModule.sendMessages(students_to_text, msgtext)

        #   Send email to administrators as well
        context['classreg'] = True
        email_content = render_to_string('email/class_cancellation_admin.txt', context)
        if email_ssis:
            context['classreg'] = False
            email_content += '\n' + render_to_string('email/class_cancellation_body.txt', context)
        to_email = ['Directors <%s>' % (self.parent_program.director_email)]
        from_email = '%s Web Site <%s>' % (self.parent_program.program_type, self.parent_program.director_email)
        send_mail(email_title, email_content, from_email, to_email)

        #   Send email to teachers
        if email_teachers:
            context['director_email'] = self.parent_program.director_email
            email_content = render_to_string('email/class_cancellation_teacher.txt', context)
            from_email = '%s at %s <%s>' % (self.parent_program.program_type, settings.INSTITUTION_NAME, self.parent_program.director_email)
            if email_ssis:
                email_content += '\n' + render_to_string('email/class_cancellation_body.txt', context)
            teachers = self.parent_class.get_teachers()
            for t in teachers:
                to_email = ['%s <%s>' % (t.name(), t.email)]
                send_mail(email_title, email_content, from_email, to_email)

        self.clearStudents()

        #   If specified, remove the class's time and room assignment.
        if unschedule:
            self.clearRooms()
            self.meeting_times.clear()

        self.status = CANCELLED
        self.save()

    def clearStudents(self):
        now = datetime.datetime.now()
        qs = StudentRegistration.valid_objects(now).filter(section=self)
        for reg in qs:
            signals.pre_save.send(sender=StudentRegistration, instance=reg)
        qs.update(end_date=now)
        #   Compensate for the lack of a signal on update().
        for reg in qs:
            signals.post_save.send(sender=StudentRegistration, instance=reg)
        if all([sec.isCancelled() for sec in self.parent_class.get_sections() if sec!=self]):
            qs_ssi = StudentSubjectInterest.valid_objects(now).filter(subject=self.parent_class)
            for ssi in qs_ssi:
                signals.pre_save.send(sender=StudentSubjectInterest, instance=ssi)
            qs_ssi.update(end_date=now)
            for ssi in qs_ssi:
                signals.post_save.send(sender=StudentSubjectInterest, instance=ssi)

    @staticmethod
    def idcmp(one, other):
        return cmp(one.id, other.id)

    def __cmp__(self, other):
        # Warning: this hits the DB around four times per comparison, i.e.,
        # O(n log n) times for a list.  Consider using prefetch_related and
        # then sorting with the key self.start_time_prefetched(), which will
        # hit the DB only once at the start, and compute the start time of each
        # class only once.
        selfevent = self.firstBlockEvent()
        otherevent = other.firstBlockEvent()

        if selfevent is not None and otherevent is None:
            return 1
        if selfevent is None and otherevent is not None:
            return -1

        if selfevent is not None and otherevent is not None:
            cmpresult = selfevent.__cmp__(otherevent)
            if cmpresult != 0:
                return cmpresult

        return cmp(self.title(), other.title())


    def firstBlockEvent(self):
        eventList = self.meeting_times.all().order_by('start')
        if eventList.count() == 0:
            return None
        else:
            return eventList[0]

    def isFull(self, ignore_changes=False, webapp=False):
        if len(self.get_meeting_times()) == 0:
            return True

        # Get time and tag values to determine what number to base class changes on
        now = datetime.datetime.now()
        switch_time = None
        if Tag.getProgramTag('switch_time_program_attendance', program=self.parent_program):
            try:
                switch_time_str = now.strftime("%Y/%m/%d ") + Tag.getProgramTag('switch_time_program_attendance', program=self.parent_program)
                switch_time = datetime.datetime.strptime(switch_time_str, "%Y/%m/%d %H:%M")
            except ValueError:
                pass
        switch_lag = None
        if Tag.getProgramTag('switch_lag_class_attendance', program = self.parent_program):
            try:
                switch_lag = int(Tag.getProgramTag('switch_lag_class_attendance', program = self.parent_program))
            except ValueError:
                pass

        # Mode 1: Base "fullness" on class attendance numbers if:
        # 1) using webapp/grid based class changes, 2) 'switch_lag_class_attendance' tag is set properly
        # 3) it is currently past the class start time + however many minutes specified in tag
        # 4) at least one student has been marked as attending the class
        if webapp and switch_lag and now >= (self.start_time_prefetchable() + timedelta(minutes=switch_lag)) and self.count_attending_students() >= 1:
            num_students = self.count_attending_students()
        # Mode 2: Base "fullness" on program attendance numbers if:
        # 1) using webapp/grid based class changes, 2) 'switch_time_program_attendance' tag is set properly
        # 3) it is currently past the time specified in tag
        # 4) at least five students have been marked as attending the program (to account for test users)
        elif webapp and switch_time and now >= switch_time and self.parent_program.currentlyCheckedInStudents().count() >= 5:
            num_students = self.num_students_checked_in()
        # Mode 3: Base "fullness" on enrollment numbers
        else:
            num_students = self.num_students()
        if (self.num_students() == self._get_capacity(ignore_changes) == 0):
            return False
        else:
            return (num_students >= self._get_capacity(ignore_changes))

    def isFullWebapp(self, ignore_changes=False):
        return self.isFull(ignore_changes = ignore_changes, webapp = True)

    def time_blocks(self):
        return self.friendly_times(raw=True)

    @cache_function
    def friendly_times(self, raw=False, include_date=False):
        """ Return a friendlier, prettier format for the times.

        If the events of this class are next to each other (within 10-minute overlap,
        the function will automatically collapse them. Thus, instead of
           ['11:00am--12:00n','12:00n--1:00pm'],

        you would get
           ['11:00am--1:00pm']
        for instance.
        """
        # if include_date is True, display the date as well (e.g., display
        # "Sun, July 10" instead of just "Sun"
        include_date = include_date or Tag.getBooleanTag(
            key='friendly_times_with_date',
            program=self.parent_program
        )

        txtTimes = []
        eventList = []

        # For now, use meeting times lookup instead of resource assignments.
        """
        classroom_type = ResourceType.get_or_create('Classroom')
        resources = Resource.objects.filter(resourceassignment__target=self).filter(res_type=classroom_type)
        events = [r.event for r in resources]
        """
        if hasattr(self, "_events"):
            events = list(self._events)
        else:
            events = list(self.meeting_times.all())

        if raw:
            txtTimes = Event.collapse(events, tol=datetime.timedelta(minutes=15))
        else:
            txtTimes = [ event.pretty_time(include_date=include_date) for event
                     in Event.collapse(events, tol=datetime.timedelta(minutes=15)) ]

        return txtTimes
    friendly_times.depend_on_m2m('program.ClassSection', 'meeting_times', lambda cs, ev: {'self': cs})

    def friendly_times_with_date(self, raw=False):
        return self.friendly_times(raw=raw, include_date=True)

    def isAccepted(self): return self.status > 0
    def isHidden(self): return self.status == HIDDEN
    def isReviewed(self): return self.status != UNREVIEWED
    def isRejected(self): return self.status == REJECTED
    def isCancelled(self): return self.status == CANCELLED
    isCanceled = isCancelled
    def isRegOpen(self): return self.registration_status == OPEN
    def isRegClosed(self): return self.registration_status == CLOSED
    def isFullOrClosed(self): return self.isFull() or self.isRegClosed()

    def status_str(self): return STATUS_CHOICES_DICT[self.status]

    def getRegistrations(self, user = None):
        """Gets all StudentRegistrations for this section and a particular user. If no user given, gets all StudentRegistrations for this section"""
        if user == None:
            return StudentRegistration.valid_objects().filter(section=self).order_by('start_date')
        else:
            return StudentRegistration.valid_objects().filter(section=self, user=user).order_by('start_date')

    def getRegVerbs(self, user, allowed_verbs=False):
        """ Get the list of reg-types that a student has on this class. """
        qs = self.getRegistrations(user).select_related('relationship')
        if not allowed_verbs:
            return [v.relationship for v in qs.distinct()]
        else:
            return [v.relationship for v in qs.filter(relationship__name__in=allowed_verbs).distinct()]

    def unpreregister_student(self, user, prereg_verb = None):
        #   New behavior: prereg_verb should be a string matching the name of
        #   RegistrationType to match (if you want to use it)

        from esp.program.models.app_ import StudentAppQuestion

        now = datetime.datetime.now()

        #   Stop all active or pending registrations
        if prereg_verb:
            qs = StudentRegistration.valid_objects(now).filter(relationship__name=prereg_verb, section=self, user=user)
            qs.update(end_date=now)
        else:
            qs = StudentRegistration.valid_objects(now).filter(section=self, user=user)
            qs.update(end_date=now)

        #   Explicitly fire the signals for saving a StudentRegistration in order to update caches
        #   since it doesn't get sent by update() above
        if qs.exists():
            signals.post_save.send(sender=StudentRegistration, instance=qs[0])

        #   If the student had blank application question responses for this class, remove them.
        app = user.getApplication(self.parent_program, create=False)
        if app:
            blank_responses = app.responses.filter(question__subject=self.parent_class, response='')
            unneeded_questions = StudentAppQuestion.objects.filter(studentappresponse__in=blank_responses)
            for q in unneeded_questions:
                app.questions.remove(q)
            blank_responses.delete()

        # Remove the student from any existing class mailing lists
        list_names = ["%s-%s" % (self.emailcode(), "students"), "%s-%s" % (self.parent_class.emailcode(), "students")]
        for list_name in list_names:
            remove_list_member(list_name, user.email)

    def preregister_student(self, user, overridefull=False, priority=1, prereg_verb = None, fast_force_create=False, webapp=False):
        if prereg_verb == None:
            scrmi = self.parent_program.studentclassregmoduleinfo
            if scrmi and scrmi.use_priority:
                prereg_verb = 'Priority/%d' % priority
            else:
                prereg_verb = 'Enrolled'

        if overridefull or fast_force_create or not self.isFull(webapp=webapp):
            #    Then, create the registration for this class.
            rt = RegistrationType.get_cached(name=prereg_verb, category='student')
            qs = self.registrations.filter(nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration'), id=user.id, studentregistration__relationship=rt)
            if fast_force_create or not qs.exists():
                sr = StudentRegistration(user=user, section=self, relationship=rt)
                sr.save()
                if fast_force_create:
                    ## That's the bare minimum to reg someone; we're done!
                    return True

                webapp_verb = "Onsite/Webapp"
                onsite_verb = 'OnSite/ChangedClasses'
                request = get_current_request()
                # If using the webapp to enroll in a class, annotate it as such
                if webapp:
                    rt, created = RegistrationType.objects.get_or_create(name=webapp_verb, category='student')
                    sr = StudentRegistration(user=user, section=self, relationship=rt)
                    sr.save()
                # If the registration was placed through OnSite Reg, annotate it as an OnSite registration
                elif request and request.user and isinstance(request.user, ESPUser) and request.user.is_morphed(request):
                    rt, created = RegistrationType.objects.get_or_create(name=onsite_verb, category='student')
                    sr = StudentRegistration(user=user, section=self, relationship=rt)
                    sr.save()

            else:
                pass

            if self.parent_program.isUsingStudentApps():
                #   Clear completion bit on the student's application if the class has app questions.
                app = user.getApplication(self.parent_program, create=False)
                if app:
                    app.set_questions()
                    if app.questions.count() > 0:
                        app.done = False
                        app.save()

            #   Add the student to the class mailing lists, if they exist
            list_names = ["%s-%s" % (self.emailcode(), "students"), "%s-%s" % (self.parent_class.emailcode(), "students")]
            for list_name in list_names:
                add_list_member(list_name, user)
            add_list_member("%s_%s-students" % (self.parent_program.program_type, self.parent_program.program_instance), user)

            return True
        else:
            #    Registration failed because the class is full.
            return False

    def prettyDuration(self):
        if self.duration is None:
            return u'N/A'

        return u'%s:%02d' % \
               (int(self.duration),
            int(round((self.duration - int(self.duration)) * 60)))

    class Meta:
        db_table = 'program_classsection'
        app_label = 'program'
        ordering = ['id']

class ClassSubject(models.Model, CustomFormsLinkModel):
    """ An ESP course.  The course includes one or more ClassSections. """

    #customforms info
    form_link_name='Course'

    title = models.TextField()
    parent_program = models.ForeignKey(Program)
    category = models.ForeignKey('ClassCategories',related_name = 'cls')
    class_info = models.TextField(blank=True)
    teachers = models.ManyToManyField(ESPUser)
    allow_lateness = models.BooleanField(default=False)
    message_for_directors = models.TextField(blank=True)
    class_size_optimal = models.IntegerField(blank=True, null=True)
    optimal_class_size_range = models.ForeignKey(ClassSizeRange, blank=True, null=True)
    allowable_class_size_ranges = models.ManyToManyField(ClassSizeRange, related_name='classsubject_allowedsizes', blank=True, null=True)
    grade_min = models.IntegerField()
    grade_max = models.IntegerField()
    class_size_min = models.IntegerField(blank=True, null=True)
    class_style = models.TextField(blank=True, null=True)
    hardness_rating = models.TextField(blank=True, null=True)
    class_size_max = models.IntegerField(blank=True, null=True)
    schedule = models.TextField(blank=True)
    prereqs  = models.TextField(blank=True, null=True)
    requested_special_resources = models.TextField(blank=True, null=True)
    directors_notes = models.TextField(blank=True, null=True)
    requested_room = models.TextField(blank=True, null=True)
    session_count = models.IntegerField(default=1)

    purchase_requests = models.TextField(blank=True, null=True)
    custom_form_data = JSONField(blank=True, null=True)

    documents = GenericRelation(Media, content_type_field='owner_type', object_id_field='owner_id')

    objects = ClassManager()

    status = models.IntegerField(choices = STATUS_CHOICES, default=UNREVIEWED)
    duration = models.DecimalField(blank=True, null=True, max_digits=5, decimal_places=2)
    meeting_times = models.ManyToManyField(Event, blank=True)

    # TODO(benkraft): backfill this on all existing sites, then make required.
    timestamp = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    @cache_function
    def get_allowable_class_size_ranges(self):
        return self.allowable_class_size_ranges.all()
    get_allowable_class_size_ranges.depend_on_m2m('program.ClassSubject', 'allowable_class_size_ranges', lambda subj, csr: {'self':subj })

    def get_sections(self):
        if not hasattr(self, "_sections") or self._sections is None:
            # We explicitly order by ID to make sure we get reproducible
            # ordering for e.g. index().
            self._sections = self.sections.order_by('id')

        return self._sections

    def getDocuments(self):
        return self.documents.all()

    def get_absolute_url(self):
        return "/manage/"+self.parent_program.url+"/manageclass/"+str(self.id)

    def get_edit_absolute_url(self):
        return "/manage/"+self.parent_program.url+"/editclass/"+str(self.id)

    @classmethod
    def ajax_autocomplete(cls, data):
        values = cls.objects.filter(title__istartswith=data).values(
                    'id', 'title').order_by('title')
        for v in values:
            v['ajax_str'] = v['title']
        return values

    def ajax_str(self):
        return self.title

    def prettyDuration(self):
        if len(self.get_sections()) <= 0:
            return u"N/A"
        else:
            return self.get_sections()[0].prettyDuration()

    def prettyrooms(self):
        if len(self.get_sections()) <= 0:
            return u"N/A"
        else:
            rooms = []

            for subj in self.get_sections():
                rooms.extend(subj.prettyrooms())

            return rooms

    def ascii_info(self):
        return self.class_info.encode('ascii', 'ignore')

    def _get_meeting_times(self):
        timeslot_id_list = []
        for s in self.get_sections():
            timeslot_id_list += s.meeting_times.all().values_list('id', flat=True)
        return Event.objects.filter(id__in=timeslot_id_list).order_by('start')
    all_meeting_times = property(_get_meeting_times)

    def _get_capacity(self):
        c = 0
        for s in self.get_sections():
            c += s.capacity
        return c
    capacity = property(_get_capacity)

    @cache_function
    def get_section(self, timeslot=None):
        """ Cache sections for a class.  Always use this function to get a class's sections. """
        # If we happen to know our own sections from a subquery:
        did_search = True

        if hasattr(self, "_sections"):
            for s in self._sections:
                if not hasattr(s, "_events"):
                    did_search = False
                    break
                if timeslot in s._events or timeslot == None:
                    return s

            if did_search: # If we did successfully search all sections, but found none in this timeslot
                return None
            #If we didn't successfully search all sections, go and do it the old-fashioned way:

        if timeslot:
            qs = self.sections.filter(meeting_times=timeslot)
            if qs.count() > 0:
                result = qs[0]
            else:
                result = None
        else:
            result = self.default_section()

        return result
    get_section.depend_on_row('program.ClassSection', lambda cs: {'self': cs.parent_class})
    get_section.depend_on_m2m('program.ClassSection', 'meeting_times', lambda cs, ev: {'self': cs})

    def default_section(self, create=True):
        """ Return the first section that was created for this class. """
        sec_qs = self.sections.order_by('id')
        if sec_qs.count() == 0:
            if create:
                return self.add_default_section()
            else:
                return None
        else:
            return sec_qs[0]

    def add_section(self, duration=None, status=None):
        """ Add a ClassSection belonging to this class. Can be run multiple times. """

        section_index = self.sections.count() + 1

        if duration is None:
            duration = self.duration
        if status is None:
            status = self.status

        new_section = ClassSection()
        new_section.parent_class = self
        new_section.duration = '%.4f' % duration
        new_section.status = status
        new_section.save()
        self.sections.add(new_section)

        self._sections = None

        return new_section

    def add_default_section(self, duration=0.0, status=UNREVIEWED):
        """ Make sure this class has a section associated with it.  This should be called
        at least once on every class.  Afterwards, additional sections can be created using
        add_section. """

        #   Support migration from currently existing classes.
        if self.status != UNREVIEWED:
            status = self.status
        if self.duration is not None and self.duration > 0:
            duration = self.duration

        if self.sections.count() == 0:
            return self.add_section(duration, status)
        else:
            return None

    def friendly_times(self):
        collapsed_times = []
        for s in self.get_sections():
            collapsed_times += s.friendly_times()
        return collapsed_times

    def prettyblocks(self):
        blocks = []

        for s in self.get_sections():
            rooms = u", ".join(s.prettyrooms())
            blocks += [(x + u" in " + rooms) for x in s.friendly_times()]

        return blocks

    @cache_function
    def get_teachers(self):
        """ Return a queryset of all teachers of this class. """
        # We might have teachers pulled in by Awesome Query Magic(tm), as in .catalog()
        if hasattr(self, "_teachers"):
            return self._teachers

        return self.teachers.all().order_by('last_name')
    get_teachers.depend_on_m2m('program.ClassSubject', 'teachers', lambda subj, event: {'self': subj})

    def students_dict(self):
        result = PropertyDict({})
        for sec in self.get_sections():
            result.merge(sec.students_dict())
        return result

    def students(self, verbs=['Enrolled']):
        result = ESPUser.objects.none()
        for sec in self.get_sections():
            result = result | sec.students(verbs=verbs)
        return result

    def num_students(self, verbs=['Enrolled']):
        result = 0
        for sec in self.get_sections():
            result += sec.num_students(verbs)
        return result

    def num_students_prereg(self):
        result = 0
        for sec in self.get_sections():
            result += sec.num_students_prereg()
        return result

    def percent_capacity(self):
        return 100 * self.num_students() / float(self.capacity)

    def max_students(self):
        return self.sections.count()*self.class_size_max

    def grades(self):
        """ Return an iterable list of the grades for a class. """
        return range(self.grade_min, self.grade_max + 1)

    def emailcode(self):
        """ Return the emailcode for this class.

        The ``emailcode`` is defined as 'first letter of category' + id.
        """
        return self.category.symbol+unicode(self.id)

    def url(self):
        return "%s/Classes/%s" % (self.parent_program.url, self.emailcode())

    def got_index_qsd(self):
        """ Returns if this class has an associated index.html QSD. """
        if hasattr(self, "_index_qsd"):
            return (self._index_qsd != 0)

        return QuasiStaticData.objects.filter(url__startswith='learn/' + self.url() + '/index').exists()

    def __unicode__(self):
        if self.title != u"":
            return u"%s: %s" % (self.id, self.title)
        else:
            return u"%s: (none)" % self.id

    def delete(self, adminoverride = False):
        if self.num_students() > 0 and not adminoverride:
            return False

        for sec in self.sections.all():
            sec.delete()

        #   Remove indirect dependencies
        self.documents.clear()

        super(ClassSubject, self).delete()

    def numStudentAppQuestions(self):
        # This field may be prepopulated by .objects.catalog()
        if not hasattr(self, "_studentapps_count"):
            self._studentapps_count = self.studentappquestion_set.count()

        return self._studentapps_count

    def pretty_teachers(self):
        """ Return a prettified string listing of the class's teachers """
        return u", ".join([ u"%s %s" % (u.first_name, u.last_name) for u in self.get_teachers() ])

    def isFull(self, ignore_changes=False, timeslot=None, webapp=False):
        """ A class subject is full if all of its sections are full. """
        if timeslot is not None:
            sections = [self.get_section(timeslot)]
        else:
            sections = self.get_sections()
        for s in sections:
            if not s.isFull(ignore_changes=ignore_changes, webapp=webapp):
                return False
        return True

    def hasScheduledSections(self):
        """ Return whether the class has at least one scheduled section.

        Only display the "class is full" message if this is true.
        """
        sections = self.get_sections()
        for s in sections:
            if len(s.get_meeting_times()) > 0:
                return True
        return False

    @cache_function
    def get_capacity_factor():
        tag_val = Tag.getTag('nearly_full_threshold')
        if tag_val:
            capacity_factor = float(tag_val)
        else:
            capacity_factor = 0.75
        return capacity_factor
    get_capacity_factor.depend_on_row('tagdict.Tag', lambda tag: {}, lambda tag: tag.key == 'nearly_full_threshold')
    get_capacity_factor = staticmethod(get_capacity_factor)

    def is_nearly_full(self, capacity_factor = None):
        if capacity_factor == None:
            capacity_factor = ClassSubject.get_capacity_factor()
        return len([x for x in self.get_sections() if x.num_students() > capacity_factor*x.capacity]) > 0

    def getTeacherNames(self):
        teachers = []
        for teacher in self.get_teachers():
            name = teacher.name()
            if name.strip() == '':
                name = teacher.username
            teachers.append(name)
        return teachers

    def getTeacherNamesLast(self):
        teachers = []
        for teacher in self.get_teachers():
            name = teacher.name_last_first()
            if name.strip() == '':
                name = teacher.username
            teachers.append(name)
        return teachers

    def cannotAdd(self, user, checkFull=True, which_section=None, webapp=False):
        """ Go through and give an error message if this user cannot add this class to their schedule. """
        if not user.isStudent():
            return u'You are not a student!'

        if not self.isAccepted():
            return u'This class is not accepted.'

        if checkFull and not self.parent_program.user_can_join(user):
            return u'This program cannot accept any more students!  Please try again in its next session.'

        if checkFull and self.isFull(webapp=webapp):
            scrmi = self.parent_program.studentclassregmoduleinfo
            return scrmi.temporarily_full_text

        if user.getGrade(self.parent_program) < self.grade_min or \
               user.getGrade(self.parent_program) > self.grade_max:
            if not Permission.user_has_perm(user, "GradeOverride", self.parent_program):
                return u'You are not in the requested grade range for this class.'

        for section in self.get_sections():
            if user.isEnrolledInClass(section):
                return u'You are already signed up for a section of this class!'

        if which_section:
            sections = [which_section]
        else:
            sections = self.get_sections()
        # check to see if there's a conflict with each section of the subject, or if the user
        # has already signed up for one of the sections of this class
        for section in sections:
            res = section.cannotAdd(user, checkFull, autocorrect_constraints=False, webapp=webapp)
            if not res: # if any *can* be added, then return False--we can add this class
                return res
        #   Pass on any errors that were triggered by the individual sections
        if res:
            return res

        # res can't have ever been False--so we must have an error. Pass it along.
        return u'This class conflicts with your schedule!'

    def makeTeacher(self, user):
        self.teachers.add(user)
        return True

    def removeTeacher(self, user):
        self.teachers.remove(user)
        return True

    def getResourceRequests(self): # get all resource requests associated with this ClassSubject
        return ResourceRequest.objects.filter(target__parent_class=self)

    def conflicts(self, teacher):
        user = teacher
        for cls in user.getTaughtClasses().filter(parent_program = self.parent_program):
            for section in cls.get_sections():
                for time in section.meeting_times.all():
                    for sec in self.sections.all().exclude(id=section.id):
                        if sec.meeting_times.filter(id = time.id).count() > 0:
                            return True


        #   Check that adding this teacher as a coteacher would not overcommit them
        #   to more hours of teaching than the program allows.
        avail = Event.collapse(user.getAvailableTimes(self.parent_program, ignore_classes=True), tol=timedelta(minutes=15))
        time_avail = 0.0
        #   Start with amount of total time pledged as available
        for tg in avail:
            td = tg.duration()
            time_avail += (td.seconds / 3600.0)
        #   Subtract out time already pledged for teaching classes other than this one
        for cls in user.getTaughtClasses(self.parent_program):
            if cls.id != self.id:
                for sec in cls.get_sections():
                    time_avail -= float(str(sec.duration))
        #   Add up time that would be needed to teach this class
        time_needed = 0.0
        for sec in self.get_sections():
            time_needed += float(str(sec.duration))
        #   See if the available time exceeds the required time
        if time_needed > time_avail:
            return True

        return False

    def isAccepted(self): return self.status > 0
    def isHidden(self): return self.status == HIDDEN
    def isReviewed(self): return self.status != UNREVIEWED
    def isRejected(self): return self.status == REJECTED
    def isCancelled(self): return self.status == CANCELLED
    isCanceled = isCancelled    # Yay alternative spellings

    def status_str(self): return STATUS_CHOICES_DICT[self.status]

    def isRegOpen(self):
        for sec in self.sections.all():
            if sec.isRegOpen():
                return True
        return False

    def isRegClosed(self):
        for sec in self.get_sections():
            if not sec.isRegClosed():
                return False
        return True

    def isFullOrClosed(self):
        for sec in self.get_sections():
            if not sec.isFullOrClosed():
                return False
        return True

    def accept(self, user=None, show_message=False):
        """ mark this class as accepted """
        if self.isAccepted():
            return False # already accepted

        self.status = ACCEPTED
        # I do not understand the following line, but it saves us from "Cannot convert float to Decimal".
        # Also seen in /esp/program/modules/forms/management.py -ageng 2008-11-01
        #self.duration = Decimal(str(self.duration))
        self.save()
        #   Accept any unreviewed sections.
        for sec in self.sections.all():
            if sec.status == UNREVIEWED:
                sec.status = ACCEPTED
                sec.save()

        if not show_message:
            return True

        subject = 'Your %s class was approved!' % (self.parent_program.niceName())

        content =  """Congratulations, your class,
%s,
was approved! Please go to http://esp.mit.edu/teach/%s/class_status/%s to view your class' status.

-esp.mit.edu Autogenerated Message""" % \
                  (self.title, self.parent_program.getUrlBase(), self.id)
        if user is None:
            user = AnonymousUser()
        return True

    def set_all_sections_to_status(self, status):
        self.status = status
        self.save()
        for sec in self.sections.all():
            sec.status = status
            sec.save()

    def accept_all_sections(self):
        """ Accept all sections of this class, without any of the checks or messages that are in accept() """
        self.set_all_sections_to_status(ACCEPTED)

    def propose(self):
        """ Mark this class as just `proposed' """
        self.status = UNREVIEWED
        self.save()

    def unreview_all_sections(self):
        """ Mark all sections of this class as unreviewed """
        self.set_all_sections_to_status(UNREVIEWED)

    def reject(self):
        """ Mark this class as rejected; also kicks out students from each section. """
        self.clearStudents()
        self.set_all_sections_to_status(REJECTED)

    def cancel(self, email_students=True, include_lottery_students=False, text_students=False, email_teachers=True, explanation=None, unschedule=False):
        """ Cancel this class by cancelling all of its sections. """
        for sec in self.sections.all():
            sec.cancel(email_students, include_lottery_students, text_students, email_teachers, explanation, unschedule)
        self.status = CANCELLED
        self.save()

    def clearStudents(self):
        for sec in self.sections.all():
            sec.clearStudents()

    @cache_function
    def docs_summary(self):
        """ Return the first three documents associated
        with a class, for previewing. """
        return self.documents.all()[:3]
    docs_summary.depend_on_model('qsdmedia.Media')

    def getUrlBase(self):
        """ Gets the base url of this class """
        return self.url()

    def getRegistrations(self, user=None):
        """Gets all non-expired StudentRegistrations associated with this class. If user is given, will also filter to that particular user only."""
        if user == None:
            return StudentRegistration.valid_objects().filter(section__in=self.sections.all()).order_by('start_date')
        else:
            return StudentRegistration.valid_objects().filter(section__in=self.sections.all(), user=user).order_by('start_date')

    def getRegVerbs(self, user):
        """ Get the list of verbs that a student has within this class. """
        return self.getRegistrations(user).values_list('relationship__name', flat=True)

    def preregister_student(self, user, overridefull=False, automatic=False):
        """ Register the student for the least full section of the class
        that fits into their schedule. """
        sections = user.getEnrolledSections()
        time_taken = []
        for c in sections:
            time_taken += list(c.meeting_times.all())

        best_section = None
        min_ratio = 1.0
        for sec in self.sections.all():
            available = True
            for t in sec.meeting_times.all():
                if t in time_taken:
                    available = False
            if available and (float(sec.num_students()) / (sec.capacity + 1)) < min_ratio:
                min_ratio = float(sec.num_students()) / (sec.capacity + 1)
                best_section = sec

        if best_section:
            best_section.preregister_student(user, overridefull, automatic)

    def unpreregister_student(self, user):
        """ Find the student's registration for the class and expire it.
        Also update the cache on each of the sections.  """
        for s in self.sections.all():
            s.unpreregister_student(user)

    def getArchiveClass(self):
        result = ArchiveClass.objects.filter(original_id=self.id)
        if result.count() > 0:
            return result[0]

        result = ArchiveClass()
        date_dir = self.parent_program.program_instance.split('_')
        result.program = self.parent_program.program_type
        result.year = date_dir[0][:4]
        if len(date_dir) > 1:
            result.date = date_dir[1]
        teacher_strs = ['%s %s' % (t.first_name, t.last_name) for t in self.get_teachers()]
        result.teacher = ' and '.join(teacher_strs)
        result.category = self.category.category[:32]
        result.title = self.title
        result.description = self.class_info
        if self.prereqs and len(self.prereqs) > 0:
            result.description += '\n\nThe prerequisites for this class were: %s' % self.prereqs
        result.teacher_ids = '|' + '|'.join([str(t.id) for t in self.get_teachers()]) + '|'
        all_students = self.students()
        result.student_ids = '|' + '|'.join([str(s.id) for s in all_students]) + '|'
        result.original_id = self.id

        #   It's good to just keep everything in the archives since they are cheap.
        result.save()

        return result

    @staticmethod
    def class_sort_by_category(one, other):
        return cmp(one.category.category, other.category.category)

    @staticmethod
    def class_sort_by_id(one, other):
        return cmp(one.id, other.id)

    @staticmethod
    def class_sort_by_teachers(one, other):
        return cmp( sorted(one.getTeacherNames()), sorted(other.getTeacherNames()) )

    @staticmethod
    def class_sort_by_title(one, other):
        return cmp(one.title, other.title)

    @staticmethod
    def class_sort_by_timeblock(one, other):
        if len(one.all_meeting_times) == 0:
            if len(other.all_meeting_times) == 0:
                return 0
            else:
                return -1
        else:
            if len(other.all_meeting_times) == 0:
                return 1
            else:
                return cmp(one.all_meeting_times[0], other.all_meeting_times[0])

    @staticmethod
    def class_sort_noop(one, other):
        return 0

    def save(self, *args, **kwargs):
        super(ClassSubject, self).save(*args, **kwargs)
        if self.status < UNREVIEWED: #ie, all rejected or cancelled classes.
            # Punt teachers all of whose classes have been rejected, from the programwide teachers mailing list
            teachers = self.get_teachers()
            for t in teachers:
                if t.getTaughtClasses(self.parent_program).filter(status__gte=10).count() == 0:
                    mailing_list_name = "%s_%s" % (self.parent_program.program_type, self.parent_program.program_instance)
                    teachers_list_name = "%s-%s" % (mailing_list_name, "teachers")
                    remove_list_member(teachers_list_name, t.email)

    class Meta:
        db_table = 'program_class'
        app_label = 'program'


class ClassCategories(models.Model):
    """ A list of all possible categories for an ESP class

    Categories include 'Mathematics', 'Science', 'Zocial Zciences', etc.
    """

    category = models.TextField(blank=False)
    symbol = models.CharField(max_length=1, default='?', blank=False)
    seq = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Class Categories'
        app_label = 'program'
        db_table = 'program_classcategories'

    def __unicode__(self):
        return u'%s (%s)' % (self.category, self.symbol)


@cache_function
def sections_in_program_by_id(prog):
    return [int(x) for x in ClassSection.objects.filter(parent_class__parent_program=prog).distinct().values_list('id', flat=True)]
sections_in_program_by_id.depend_on_model(ClassSection)
sections_in_program_by_id.depend_on_model(ClassSubject)

def install():
    """ Initialize the default class categories. """
    logger.info("Installing esp.program.class initial data...")
    category_dict = {
        'S': 'Science',
        'M': 'Math & Computer Science',
        'E': 'Engineering',
        'A': 'Arts',
        'H': 'Humanities',
        'X': 'Miscellaneous',
    }

    if not ClassCategories.objects.exists():
        for key in category_dict:
            ClassCategories.objects.create(symbol=key, category=category_dict[key])
