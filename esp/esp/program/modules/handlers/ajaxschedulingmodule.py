
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
from esp.program.modules.base    import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.modules.admin_search import AdminSearchEntry, SEARCH_CATEGORY_CLASSES
from esp.program.modules         import program_settings
from esp.program.models          import ClassSection
from esp.utils.web               import render_to_response
from django.http                 import HttpResponse
from esp.cal.models              import Event
from esp.users.models            import ESPUser
from esp.middleware              import ESPError
from esp.resources.models        import Resource, ResourceAssignment
from esp.tagdict.models          import Tag
from argcache                    import cache_function
from uuid                        import uuid4 as get_uuid
from esp.utils.decorators        import json_response

import json
import time

_MAX_INT32 = 2**31 - 1


def _parse_pos_int32(value):
    """Return a positive 32-bit integer from value, or None if invalid or out of range."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        pk = value
    elif isinstance(value, str):
        token = value.strip()
        if not (token.isascii() and token.isdigit()):
            return None
        try:
            pk = int(token)
        except ValueError:
            return None
    else:
        return None
    if pk < 1 or pk > _MAX_INT32:
        return None
    return pk


def _get_program_section(prog, raw_id):
    """Return the ClassSection matching raw_id within prog, or None if invalid or foreign."""
    sec_id = _parse_pos_int32(raw_id)
    if sec_id is None:
        return None
    return ClassSection.objects.filter(
        id=sec_id,
        parent_class__parent_program=prog,
    ).first()


class AJAXSchedulingModule(ProgramModuleObj):
    doc = """Provides an application to use for scheduling classes."""

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "AJAX Scheduling",
            "module_type": "manage",
            "seq": 7,
            "choosable": 1,
            }

    @classmethod
    def get_admin_search_entry(cls, program, tl, view_name, pmo):
        if view_name != "ajax_scheduling":
            return None
        base = program.getUrlBase()
        return AdminSearchEntry(
            id="manage_ajax_scheduling",
            url="/manage/%s/ajax_scheduling" % base,
            title="Scheduling",
            category=SEARCH_CATEGORY_CLASSES,
            keywords=["schedule", "rooms", "times", "ajax", "scheduling"],
        )

    def prepare(self, context=None):
        if context is None:
            context = {}

        context['schedulingmodule'] = self
        return context

    @main_call
    @needs_admin
    def ajax_scheduling(self, request, tl, one, two, module, extra, prog):
        """
        Serve the scheduling page.

        This is just a static page;
        it gets all of its content from AJAX callbacks.
        """

        #trim the log here.
        #Nothing special about right here, but putting it here makes sure it's done regularly, without
        #doing it really really often, and without having an extra thread just for that.

        self.get_change_log(prog).prune()

        #actually return the page
        context = {
            "has_autoscheduler_frontend": prog.hasModule("AutoschedulerFrontendModule"),
            "has_moderator_module": prog.hasModule("TeacherModeratorModule"),
            "contiguous_tolerance": Tag.getProgramTag('timeblock_contiguous_tolerance', program = prog)
            }

        return render_to_response(self.baseDir()+'ajax_scheduling.html', request, context)

    @aux_call
    @needs_admin
    def ajax_schedule_assignments_csv(self, request, tl, one, two, module, extra, prog):
        lst = []
        for s in prog.sections():
            if s.resourceassignment_set.all().count() > 0:
                ra = s.resourceassignment_set.all().order_by('resource__event__id')[0]
                lst.append((s.id, ra.resource.name, ra.resource.event.id))

        return HttpResponse('\n'.join([','.join(['"%s"' % v for v in x]) for x in lst]), content_type='text/csv')

    #helper functions for ajax_schedule_class
    #separated out here to make code more readable and enable testing
    def makeret(self, prog, **kwargs):
        last_changed = self.ajax_schedule_last_changed_helper(prog).raw_value
        kwargs['val'] = last_changed['val']
        response = HttpResponse(content_type="application/json")
        json.dump(kwargs, response)
        return response

    def ajax_schedule_deletereg(self, prog, cls, user=None):
        if cls is None or cls.parent_class.parent_program_id != prog.id:
            return self.makeret(prog, ret=False, msg="Class section not found in this program.")
        cls.clearRooms()
        cls.clear_meeting_times()
        self.get_change_log(prog).appendScheduling([], "", int(cls.id), user)

        return self.makeret(prog, ret=True, msg="Schedule removed for Class Section '%s'" % cls.emailcode())

    def ajax_schedule_assignreg(self, prog, cls, timeslot_ids, classroom_ids, user=None, override=False):
        if cls is None or cls.parent_class.parent_program_id != prog.id:
            return self.makeret(prog, ret=False, msg="Class section not found in this program.")

        if len(timeslot_ids) < 1:
            return self.makeret(prog, ret=False, msg="No times specified!, can't assign to a timeblock")

        if len(classroom_ids) < 1:
            return self.makeret(prog, ret=False, msg="No classrooms specified!, can't assign to a timeblock")

        parsed_timeslot_ids = [_parse_pos_int32(ts_id) for ts_id in timeslot_ids]
        if any(ts_id is None for ts_id in parsed_timeslot_ids):
            return self.makeret(prog, ret=False, msg="Specified Events not found in the database")

        parsed_classroom_ids = [_parse_pos_int32(c_id) for c_id in classroom_ids]
        if any(c_id is None for c_id in parsed_classroom_ids):
            return self.makeret(prog, ret=False, msg="Specified Classrooms not found in the database")

        basic_cls = parsed_classroom_ids[0]
        for c in parsed_classroom_ids:
            if c != basic_cls:
                return self.makeret(prog, ret=False, msg="Assigning one section to multiple rooms.  This interface doesn't support this feature currently; assign it to one room for now and poke a Webmin to do this for you manually.")

        times = Event.objects.filter(id__in=parsed_timeslot_ids, program=prog).order_by('start')
        if len(times) < 1 or len(times) != len(set(parsed_timeslot_ids)):
            return self.makeret(prog, ret=False, msg="Specified Events not found in the database")

        classrooms = Resource.objects.filter(id=basic_cls, res_type__name="Classroom")
        if len(classrooms) < 1:
            return self.makeret(prog, ret=False, msg="Specified Classrooms not found in the database")

        classroom = classrooms[0]

        cannot_schedule = False
        if not override:
            cannot_schedule = cls.cannotSchedule(times, ignore_classes=False)
        if cannot_schedule:
            return self.makeret(prog, ret=False, msg=cannot_schedule)

        cls.assign_meeting_times(times)
        status, errors = cls.assign_room(classroom, clear_others=True)

        if not status: # If we failed any of the scheduling-constraints checks in assign_room()
            cls.clear_meeting_times()
            return self.makeret(prog, ret=False, msg=" | ".join(errors))

        #add things to the change log here
        self.get_change_log(prog).appendScheduling([int(t.id) for t in times], basic_cls, int(cls.id), user)

        return self.makeret(prog, ret=True, msg="Class Section '%s' successfully scheduled" % cls.emailcode())

    def ajax_schedule_swap(self, prog, assignments, user=None, override=False):
        # assignments: the list of new assignments for the section(s) in json format
        if not isinstance(assignments, list):
            return self.makeret(prog, ret=False, msg="Assignments must be a list.")

        validated = []
        for asmt in assignments:
            if not isinstance(asmt, dict):
                return self.makeret(prog, ret=False, msg="Invalid assignment entry.")
            cls = _get_program_section(prog, asmt.get('section'))
            if cls is None:
                return self.makeret(prog, ret=False, msg="Class section not found in this program.")
            room_id = asmt.get('room_id')
            if room_id:
                parsed_room = _parse_pos_int32(room_id)
                raw_timeslots = asmt.get('timeslots')
                if parsed_room is None or not isinstance(raw_timeslots, list) or not raw_timeslots:
                    return self.makeret(prog, ret=False, msg="Invalid assignment entry.")
                parsed_timeslots = [_parse_pos_int32(ts) for ts in raw_timeslots]
                if any(ts is None for ts in parsed_timeslots):
                    return self.makeret(prog, ret=False, msg="Invalid assignment entry.")
                validated.append((cls, parsed_room, parsed_timeslots))
            else:
                validated.append((cls, None, []))

        # Unschedule all of the section(s)
        for cls, _, _ in validated:
            retval = self.ajax_schedule_deletereg(prog, cls, user)
            if not json.loads(retval.content)['ret']:
                return retval

        # Reschedule all of the section(s)
        for cls, room_id, timeslots in validated:
            if room_id is not None:
                retval = self.ajax_schedule_assignreg(prog, cls, timeslots, [room_id], user, override)
                if not json.loads(retval.content)['ret']:
                    return retval

        return self.makeret(prog, ret=True, msg="Class sections successfully swapped")

    @aux_call
    @needs_admin
    @json_response()
    def ajax_change_log(self, request, tl, one, two, module, extra, prog):
        cl = self.get_change_log(prog)
        try:
            last_fetched_index = int(request.GET.get('last_fetched_index', 0))
        except (ValueError, TypeError):
            last_fetched_index = 0
        if last_fetched_index < -_MAX_INT32 - 1 or last_fetched_index > _MAX_INT32:
            last_fetched_index = 0

        #check whether we have a log entry at least as old as the last fetched time
        #if not, we return a command to reload instead of the log
        #note: negative number implies we want to debug dump changelog
        if cl.get_earliest_index() is not None and last_fetched_index !=0 and cl.get_earliest_index() > last_fetched_index:
            return { "other" : [ { 'command' : "reload", 'earliest_index' : cl.get_earliest_index(), 'latest_index' : cl.get_latest_index(), 'time' : time.time() } ] }

        return { "changelog" : cl.get_log(last_fetched_index), 'other' : [ { 'time': time.time() } ] }

    @aux_call
    @needs_admin
    def ajax_clear_change_log(self, request, tl, one, two, module, extra, prog):
        """ This call exists for debugging and testing purposes.  It's not a disaster if it's
        called in production, but it is annoying.
        Clears the change log for this program. """

        if request.method != 'POST':
            return HttpResponse('Method not allowed. Use POST.', status=405)

        self.get_change_log(prog).entries.all().delete()
        context = {}
        return render_to_response(self.baseDir()+'clear_cache_confirmation.html', request, context)

    def get_change_log(self, prog):
        change_log = program_settings.AJAXChangeLog.objects.filter(program=prog)

        if change_log.count() == 0:
            change_log = program_settings.AJAXChangeLog()
            change_log.update(prog)
            change_log.save()
        else:
            change_log = change_log[0]

        return change_log

    @aux_call
    @needs_admin
    @json_response()
    def ajax_section_details(self, request, tl, one, two, module, extra, prog):
        sectionDetails = {}
        for sectionDetail in program_settings.AJAXSectionDetail.objects.filter(program=prog):
            sectionDetails[sectionDetail.cls_id] = [{'comment': sectionDetail.comment, 'locked': sectionDetail.locked}]
        return sectionDetails

    @aux_call
    @needs_admin
    def ajax_schedule_class(self, request, tl, one, two, module, extra, prog):
        # DON'T CACHE this function!
        # It's supposed to have side effects, that's the whole point!
        if not 'action' in request.POST:
            raise ESPError("This URL is intended to be used for client<->server communication; it's not for human-readable content.", log=False)

        # Pull relevant data out of the JSON structure
        action = request.POST['action']

        if action == 'deletereg':
            cls = _get_program_section(prog, request.POST.get('cls'))
            if cls is None:
                return self.makeret(prog, ret=False, msg="Class section not found in this program.")
            retval = self.ajax_schedule_deletereg(prog, cls, request.user)
        elif action == 'assignreg':
            cls = _get_program_section(prog, request.POST.get('cls'))
            if cls is None:
                return self.makeret(prog, ret=False, msg="Class section not found in this program.")
            raw_assignments = request.POST.get('block_room_assignments', '')
            times = []
            classrooms = []
            for br in raw_assignments.splitlines():
                br = br.strip()
                if not br:
                    continue
                if ',' not in br:
                    return self.makeret(prog, ret=False, msg="Invalid block room assignment.")
                timeslot, classroom = br.split(",", 1)
                ts_id = _parse_pos_int32(timeslot)
                room_id = _parse_pos_int32(classroom)
                if ts_id is None or room_id is None:
                    return self.makeret(prog, ret=False, msg="Invalid block room assignment.")
                times.append(ts_id)
                classrooms.append(room_id)
            override = request.POST.get('override') == "true"
            retval = self.ajax_schedule_assignreg(prog, cls, times, classrooms, request.user, override)
        elif action == 'swap':
            raw_assignments = request.POST.get('assignments')
            if not raw_assignments:
                return self.makeret(prog, ret=False, msg="No assignments specified.")
            try:
                assignments = json.loads(raw_assignments)
            except (ValueError, TypeError):
                return self.makeret(prog, ret=False, msg="Invalid assignments JSON.")
            override = request.POST.get('override') == "true"
            retval = self.ajax_schedule_swap(prog, assignments, request.user, override)
        else:
            return self.makeret(prog, ret=False, msg="Unrecognized command: '%s'" % action)

        return retval

    @aux_call
    @needs_admin
    def ajax_assign_moderator(self, request, tl, one, two, module, extra, prog):
        # DON'T CACHE this function!
        # It's supposed to have side effects, that's the whole point!
        if 'action' not in request.POST:
            raise ESPError("This URL is intended to be used for client<->server communication; it's not for human-readable content.", log=False)

        action = request.POST['action']
        if action not in ('removemod', 'assignmod'):
            return self.makeret(prog, ret=False, msg="Unrecognized command: '%s'" % action)

        # Pull relevant data out of the JSON structure
        sec = _get_program_section(prog, request.POST.get('sec'))
        if sec is None:
            return self.makeret(prog, ret=False, msg="Class section not found in this program.")

        mod_id = _parse_pos_int32(request.POST.get('mod'))
        mod = ESPUser.objects.filter(id=mod_id).first() if mod_id is not None else None
        if mod is None:
            return self.makeret(prog, ret=False, msg="Moderator not found.")

        if action == 'removemod':
            sec.moderators.remove(mod)
            self.get_change_log(prog).appendModerator(mod.id, sec.id, False, request.user)
            return self.makeret(prog, ret=True, msg=f"Moderator '{mod.name()}' removed from Class Section '{sec.emailcode()}'")
        else:
            override = request.POST.get('override') == "true"
            if not override:
                # check availability
                avail_times = [t.id for t in mod.getAvailableTimes(prog)]
                for t in sec.meeting_times.all():
                    if t.id not in avail_times:
                        return self.makeret(prog, ret=False, msg=f"Moderator '{mod.name()}' is not available to moderate Class Section '{sec.emailcode()}'")
            sec.moderators.add(mod)
            self.get_change_log(prog).appendModerator(mod.id, sec.id, True, request.user)
            return self.makeret(prog, ret=True, msg=f"Moderator '{mod.name()}' assigned to Class Section '{sec.emailcode()}'")

    @aux_call
    @needs_admin
    def ajax_set_comment(self, request, tl, one, two, module, extra, prog):
        if 'comment' not in request.POST:
            raise ESPError("This URL is intended to be used for client<->server communication; it's not for human-readable content.", log=False)

        # Pull relevant data out of the JSON structure
        cls = _get_program_section(prog, request.POST.get('cls'))
        if cls is None:
            return self.makeret(prog, ret=False, msg="Class section not found in this program.")
        comment = request.POST['comment']
        locked = 'locked' in request.POST

        section_detail = program_settings.AJAXSectionDetail.objects.filter(
            program=prog, cls_id=cls.id
        ).first()
        if section_detail is not None:
            section_detail.update(comment, locked)
        else:
            section_detail = program_settings.AJAXSectionDetail()
            section_detail.initialize(prog, cls.id, comment, locked)

        self.get_change_log(prog).appendComment(comment, locked, cls.id, request.user)
        return self.makeret(prog, ret=True, msg="Class Section #%s successfully updated" % cls.id)

    @aux_call
    @needs_admin
    def ajax_schedule_last_changed(self, request, tl, one, two, module, extra, prog):
        return self.ajax_schedule_last_changed_helper(prog)

    def ajax_schedule_last_changed_helper(self, prog):
        ret = { 'val': str(self.ajax_schedule_get_uuid(prog)),
                'msg': 'UUID that changes every time the schedule is updated',
                'time' : time.time(),
                'latest_index' : self.get_change_log(prog).get_latest_index() }

        response = HttpResponse(content_type="application/json")
        json.dump(ret, response)
        response.raw_value = ret  # So that other functions can call this view and get the original return value back
        return response

    @cache_function
    def ajax_schedule_get_uuid(self, prog):
        return get_uuid()

    # This function should be called iff the data returned by any of the other ajax_ JSON functions changes.
    # So, cache it; and have the cache expire whenever any of the relevant models changes.
    # Yeah, the cache will get expired quite often...; but, eh, it's a cheap function.
    ajax_schedule_get_uuid.get_or_create_token(('prog',))
    ajax_schedule_get_uuid.depend_on_model('resources.ResourceAssignment')
    ajax_schedule_get_uuid.depend_on_model('resources.Resource')
    ajax_schedule_get_uuid.depend_on_model('resources.ResourceRequest')
    ajax_schedule_get_uuid.depend_on_model('cal.Event')
    ajax_schedule_get_uuid.depend_on_model('program.ClassSection')
    ajax_schedule_get_uuid.depend_on_model('program.ClassSubject')
    ajax_schedule_get_uuid.depend_on_model('users.UserAvailability')

    @cache_function
    def ajax_lunch_timeslots_cached(self, prog):
        data = list(prog.lunch_timeslots().values_list('id', flat=True))
        response = HttpResponse(content_type="application/json")
        json.dump(data, response)
        return response
    ajax_lunch_timeslots_cached.get_or_create_token(('prog',))
    ajax_lunch_timeslots_cached.depend_on_row('cal.Event',
                                              lambda e: {'prog': e.program} if e.program_id else {})
    ajax_lunch_timeslots_cached.depend_on_row('program.ClassSection',
                                              lambda sec: {'prog': sec.parent_class.parent_program})
    ajax_lunch_timeslots_cached.depend_on_row('program.ClassSubject',
                                              lambda cls: {'prog': cls.parent_program})
    ajax_lunch_timeslots_cached.depend_on_model('program.ClassCategories')
    ajax_lunch_timeslots_cached.depend_on_m2m('program.ClassSection', 'meeting_times', lambda sec, event: {'prog': sec.parent_class.parent_program})

    @aux_call
    @needs_admin
    def ajax_lunch_timeslots(self, request, tl, one, two, module, extra, prog):
        return self.ajax_lunch_timeslots_cached(prog)

    @aux_call
    @needs_admin
    def ajax_clear_schedule(self, request, tl, one, two, module, extra, prog):
        """ A view that you can use to remove schedule assignments for all class
            sections below a certain lock level.
            Be very careful using this view since it can sometimes work quite well,
            and there is currently no backup.
        """
        try:
            lock_level = int(request.POST.get('lock_level', '0'))
        except (ValueError, TypeError):
            lock_level = 0

        if request.method == 'POST':
            num_affected_sections = self.clear_schedule_logic(prog, lock_level)
            data = {'message': f'Cleared schedule assignments for {num_affected_sections} sections.'}
            response = HttpResponse(content_type="application/json")
            json.dump(data, response)
        else:
            context = {}
            context['num_affected_sections'] = self._get_affected_sections(prog, lock_level).count()
            response = render_to_response(self.baseDir()+'clear_schedule_confirmation.html', request, context)

        return response

    def _get_affected_sections(self, prog, lock_level=0):
        """
        Returns a QuerySet for ClassSection instances filtered  by parent_program and lock_level
        """
        return ClassSection.objects.filter(parent_class__parent_program=prog, resourceassignment__lock_level__lte=lock_level)

    def clear_schedule_logic(self, prog, lock_level=0):
        affected_sections = self._get_affected_sections(prog, lock_level)

        ResourceAssignment.objects.filter(target__in=affected_sections, lock_level__lte=lock_level).delete()
        ResourceAssignment.objects.filter(target__isnull=True, target_subj__isnull=True).delete()

        num_affected_sections = 0
        for section in affected_sections:
            section.meeting_times.clear()
            num_affected_sections += 1

        return num_affected_sections

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
