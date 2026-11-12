__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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

from datetime import datetime
from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.tests.support import ProgramManagerTestHelper
from esp.program.modules.program_settings import AJAXChangeLog, AJAXSectionDetail
from esp.tests.factories import make_class, make_program
import json
import time

class AJAXSchedulingModuleTestBase(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj
        # Set up the program -- we want to be sure of these parameters
        kwargs.update({
            'num_rooms': 4,
            'num_timeslots': 4, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 3, 'classes_per_teacher': 2, 'sections_per_class': 1
            })
        super().setUp(*args, **kwargs)
        self.program_manager = ProgramManagerTestHelper(self.client, self.program, self.teachers, self.rooms, self.timeslots)

        # Set the section durations to 1:50
        for sec in self.program.sections():
            sec.duration = '1.83'
            sec.save()

        #some useful urls
        self.ajax_url_base = f'/manage/{self.program.getUrlBase()}/'
        self.changelog_url = self.ajax_url_base + 'ajax_change_log'
        self.schedule_class_url = f'/manage/{self.program.getUrlBase()}/ajax_schedule_class'


    def loginAdmin(self):
        """Log in an admin user."""
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'), "Failed to log in admin user.")

    def emptySchedule(self):
        """Empty the schedule and teacher availability."""
        for s in self.program.sections():
            s.clearRooms()
            s.clear_meeting_times()
        for t in self.teachers:
            t.clearAvailableTimes(self.program)

    def forceAvailability(self):
        for teacher in self.teachers:
            for ts in self.program.getTimeSlots():
                teacher.addAvailableTime(self.program, ts)


    def clearScheduleAvailability(self):
        self.emptySchedule()
        self.loginAdmin()
        self.forceAvailability()

class AJAXSchedulingModuleTest(AJAXSchedulingModuleTestBase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.changelog, created = AJAXChangeLog.objects.get_or_create(program=self.program)

    def testModelAPI(self):
        """Schedule classes using the on-model methods."""
        self.emptySchedule()

        # Fetch three consecutive vacancies in one room.
        rooms = self.rooms[0].identical_resources().filter(event__in=self.timeslots).order_by('event__start')
        self.assertTrue(rooms.count() >= 3, "Not enough timeslots to run this test.")

        # Now we attempt to schedule the sections overlapping.
        s1, s2 = [t.getTaughtSections(self.program)[0] for t in self.teachers[:2]]

        # First, meeting times should be assigned without trouble.
        m1 = [rooms[0].event, rooms[1].event]
        m2 = [rooms[1].event, rooms[2].event]
        s1.assign_meeting_times(m1)
        s2.assign_meeting_times(m2)
        self.assertTrue(set(s1.get_meeting_times()) == set(m1), "Failed to assign meeting times.")
        self.assertTrue(set(s2.get_meeting_times()) == set(m2), "Failed to assign meeting times.")

        # Return values should be success on the first one and failure on the second.
        self.assertTrue(s1.assign_room(rooms[0])[0] == True, "Received negative response when scheduling first class.")
        self.assertTrue(set(s1.classrooms()) == set(rooms[:2]), "Failed to schedule first class.")
        self.assertTrue(s2.assign_room(rooms[0])[0] == False, "Failed to detect conflict with first class.")

        # Check that the second attempt did not take.
        self.assertTrue(set(s1.classrooms()) == set(rooms[:2]), "First class's schedule modified.")
        self.assertTrue(not s2.classrooms().exists(), "Second class should not have any classrooms assigned.")


    def testWebAPI(self):
        """Schedule classes using the ajax_schedule_class view."""
        self.clearScheduleAvailability()

        # Attempt to give a teacher a schedule conflict.
        t = self.teachers[0]

        # Fetch two consecutive vacancies in two different rooms
        rooms = self.rooms[0].identical_resources().filter(event__in=self.timeslots).order_by('event__start')
        self.assertTrue(rooms.count() >= 2, "Not enough timeslots to run this test.")
        a1 = '\n'.join([f'{r.event.id},{r.identical_id()}' for r in rooms[0:2]])
        rooms = self.rooms.exclude(name=rooms[0].name)[0].identical_resources().filter(event__in=self.timeslots).order_by('event__start')
        self.assertTrue(rooms.count() >= 2, "Not enough timeslots to run this test.")
        a2 = '\n'.join([f'{r.event.id},{r.identical_id()}' for r in rooms[0:2]])

        # Schedule one class.
        ajax_url = f'/manage/{self.program.getUrlBase()}/ajax_schedule_class'
        s1, s2 = t.getTaughtSections(self.program)[:2]
        timeslots = self.program.getTimeSlots().order_by('start')
        self.client.post(ajax_url, {'action': 'deletereg', 'cls': s1.id})
        self.client.post(ajax_url, {'action': 'assignreg', 'cls': s1.id, 'block_room_assignments': a1, 'override': 'false'})
        self.assertTrue(set(s1.get_meeting_times()) == set(timeslots[0:2]), "Failed to assign meeting times.")
        # Try to schedule the other class.
        self.client.post(ajax_url, {'action': 'deletereg', 'cls': s2.id})
        self.client.post(ajax_url, {'action': 'assignreg', 'cls': s2.id, 'block_room_assignments': a2, 'override': 'false'})
        self.assertTrue(set(s1.get_meeting_times()) == set(timeslots[0:2]), "Existing meeting times clobbered.")
        self.assertTrue(set(s2.get_meeting_times()) == set(), "Failed to prevent teacher conflict.")


    #############################################################
    #
    #   Changelog tests
    #
    #############################################################
    #TODO:  is there a reason we send the time back?
    #TODO:  make the system handle last fetched index 0
    #TODO:  think about test cleanup.
    def testChangeLog(self):
        self.clearScheduleAvailability()

        #put something in the changelog to fetch
        self.program_manager.scheduleClass()

        #fetch the changelog
        changelog_response = self.client.get(self.changelog_url, {'last_fetched_index': 0 })
        self.assertTrue(changelog_response.status_code == 200, "Changelog not successfully retreieved")
        changelog = json.loads(changelog_response.content)["changelog"]
        self.assertTrue(len(changelog) == 1, "Change log does not contain exactly one class: " + str(changelog) )

    #TODO use a new program for each test
    def testChangeLogIndexZero(self):
        self.clearScheduleAvailability()
        self.program_manager.scheduleClass()
        changelog_response = self.client.get(self.changelog_url, {'last_fetched_index': 0 })
        changelog = json.loads(changelog_response.content)["changelog"]
        self.assertTrue(len(changelog) == 1, "Change log does not contain exactly one class: " + str(changelog) )


    def testChangeLogUnscheduledClasses(self):
        self.clearScheduleAvailability()

        (section, times, rooms, success) = self.program_manager.scheduleClass()
        self.assertTrue(success)

        self.program_manager.unschedule_class(section.id)

        #change log should include unscheduled classes
        changelog_response = self.client.get(self.changelog_url, {'last_fetched_index': 1 })
        changelog = json.loads(changelog_response.content)["changelog"]
        self.assertTrue(len(changelog) == 1, "Change log did not contain the unscheduled class: " + str(changelog))
        entry = changelog[0]
        self.assertEqual(entry['id'], section.id, "Change log entry was for the wrong class section: " + str(changelog))
        self.assertTrue(entry['is_scheduling'], "Change log entry should be a scheduling entry: " + str(changelog))
        self.assertEqual(entry['timeslots'], [], "Timeslots should be empty for an unscheduled class: " + str(changelog))
        self.assertEqual(entry['room_name'], '', "Room name should be empty for an unscheduled class: " + str(changelog))

    def testChangeLogFailedScheduling(self):
        #change log should not include failed scheduling of classes
        self.clearScheduleAvailability()
        (s1, times, rooms, success) = self.program_manager.scheduleClass()
        self.assertTrue(success)

        #Long setup to create an unsuccessful scheduling attempt
        #choose another section taught by the same teacher
        teacher = s1.parent_class.get_teachers()[0]
        sections = [s2 for s2 in teacher.getTaughtSections() if s2.id != s1.id]
        assert len(sections) > 0
        #our test set up makes this true, but we want to be notified if this changes and tests are going to break because of it
        s2 = sections[0]
        #schedule it
        (section, times, rooms, success) = self.program_manager.scheduleClass(section=s2, timeslots=times, rooms=rooms)
        self.assertFalse(success)

        #change log should not include it
        changelog_response = self.client.get(self.changelog_url, {'last_fetched_index': 1 })
        changelog = json.loads(changelog_response.content)["changelog"]
        self.assertTrue(len(changelog) == 0, "Change log shows unsuccessfully scheduled class: " + str(changelog))

    def test_prepare_default_context_independent_across_calls(self):
        """Separate calls to prepare() without context must receive independent dictionaries."""
        moduleobj = self.program.getModule('AJAXSchedulingModule')
        res1 = moduleobj.prepare()
        res2 = moduleobj.prepare()
        self.assertIsNot(res1, res2)
        res1['injected_leak'] = 'leaked_data'
        res3 = moduleobj.prepare()
        self.assertNotIn('injected_leak', res3)
        self.assertEqual(res3['schedulingmodule'], moduleobj)

    def test_prepare_explicit_context_preserved(self):
        """Explicit context dictionary must be preserved and mutated."""
        moduleobj = self.program.getModule('AJAXSchedulingModule')
        explicit_ctx = {'initial_key': 'initial_val'}
        res = moduleobj.prepare(explicit_ctx)
        self.assertIs(res, explicit_ctx)
        self.assertEqual(res['initial_key'], 'initial_val')
        self.assertEqual(res['schedulingmodule'], moduleobj)

    def test_prepare_explicit_empty_dict_preserved(self):
        """An explicit empty dictionary {} must not be replaced by a new dictionary."""
        moduleobj = self.program.getModule('AJAXSchedulingModule')
        empty_ctx = {}
        res = moduleobj.prepare(empty_ctx)
        self.assertIs(res, empty_ctx)
        self.assertEqual(res['schedulingmodule'], moduleobj)

    def _create_other_program_section(self):
        """Create a separate program with its own scheduled section for scoping tests."""
        other_program = make_program(
            program_type='OtherProgram',
            instance_name='2223_Fall',
            instance_label='Fall 2223',
            start_time=datetime(2223, 7, 7, 7, 5),
            num_timeslots=4,
            timeslot_length=50,
            timeslot_gap=10,
            num_rooms=2,
            admins=[self.admins[0]],
            categories=self.categories,
        )
        other_cls = make_class(
            other_program,
            self.teachers[0],
            title='Other Program Class',
            duration=1.83,
            accept=True,
        )
        other_sec = other_cls.get_sections().first()
        other_times = list(other_program.getTimeSlots().order_by('start')[:2])
        other_room = other_program.getClassrooms(other_times[0]).first()
        other_sec.assign_meeting_times(other_times)
        ok, _ = other_sec.assign_room(other_room, clear_others=True)
        self.assertTrue(ok)
        return other_program, other_sec, other_times, other_room

    def test_cross_program_scoping(self):
        """Verify AjaxSchedulingModule endpoints reject sections and timeslots from other programs."""
        self.clearScheduleAvailability()
        other_program, other_sec, other_times, _ = self._create_other_program_section()
        own_sec = self.teachers[0].getTaughtSections(self.program)[0]
        own_times = list(self.timeslots.order_by('start')[:2])
        own_room = self.rooms[0].identical_resources().filter(event=own_times[0]).first()

        # Schedule own_sec so we can verify atomic swap failure does not unschedule it
        r_sched = self.client.post(
            self.schedule_class_url,
            {
                'action': 'assignreg',
                'cls': own_sec.id,
                'block_room_assignments': '\n'.join(
                    f'{ts.id},{own_room.identical_id()}' for ts in own_times
                ),
                'override': 'false',
            },
        )
        self.assertTrue(json.loads(r_sched.content)['ret'])
        initial_changelog_count = self.changelog.entries.count()

        # 1. deletereg against foreign section is rejected
        r_del = self.client.post(
            self.schedule_class_url,
            {'action': 'deletereg', 'cls': other_sec.id},
        )
        self.assertEqual(r_del.status_code, 200)
        self.assertFalse(json.loads(r_del.content)['ret'])
        self.assertEqual(set(other_sec.get_meeting_times()), set(other_times))
        self.assertTrue(other_sec.classrooms().exists())

        # 2. assignreg against foreign section is rejected
        r_assign = self.client.post(
            self.schedule_class_url,
            {
                'action': 'assignreg',
                'cls': other_sec.id,
                'block_room_assignments': f'{own_times[0].id},{own_room.identical_id()}',
                'override': 'true',
            },
        )
        self.assertEqual(r_assign.status_code, 200)
        self.assertFalse(json.loads(r_assign.content)['ret'])
        self.assertEqual(set(other_sec.get_meeting_times()), set(other_times))

        # 3. assignreg with foreign timeslots against own section is rejected
        unscheduled_sec = self.teachers[0].getTaughtSections(self.program)[1]
        r_foreign_ts = self.client.post(
            self.schedule_class_url,
            {
                'action': 'assignreg',
                'cls': unscheduled_sec.id,
                'block_room_assignments': '\n'.join(
                    f'{ts.id},{own_room.identical_id()}' for ts in other_times
                ),
                'override': 'true',
            },
        )
        self.assertEqual(r_foreign_ts.status_code, 200)
        self.assertFalse(json.loads(r_foreign_ts.content)['ret'])
        self.assertFalse(unscheduled_sec.get_meeting_times().exists())

        # 4. swap mixing own + foreign section rejects before mutating own_sec
        r_swap = self.client.post(
            self.schedule_class_url,
            {
                'action': 'swap',
                'assignments': json.dumps([
                    {'section': own_sec.id, 'timeslots': [], 'room_id': None},
                    {'section': other_sec.id, 'timeslots': [], 'room_id': None},
                ]),
                'override': 'true',
            },
        )
        self.assertEqual(r_swap.status_code, 200)
        self.assertFalse(json.loads(r_swap.content)['ret'])
        self.assertEqual(set(own_sec.get_meeting_times()), set(own_times))
        self.assertEqual(set(other_sec.get_meeting_times()), set(other_times))

        # 5. ajax_assign_moderator assignmod / removemod against foreign section is rejected
        mod_url = self.ajax_url_base + 'ajax_assign_moderator'
        mod_user = self.teachers[1]
        r_mod_add = self.client.post(
            mod_url,
            {'action': 'assignmod', 'sec': other_sec.id, 'mod': mod_user.id, 'override': 'true'},
        )
        self.assertEqual(r_mod_add.status_code, 200)
        self.assertFalse(json.loads(r_mod_add.content)['ret'])
        self.assertFalse(other_sec.moderators.filter(id=mod_user.id).exists())

        other_sec.moderators.add(mod_user)
        r_mod_rem = self.client.post(
            mod_url,
            {'action': 'removemod', 'sec': other_sec.id, 'mod': mod_user.id},
        )
        self.assertEqual(r_mod_rem.status_code, 200)
        self.assertFalse(json.loads(r_mod_rem.content)['ret'])
        self.assertTrue(other_sec.moderators.filter(id=mod_user.id).exists())

        # 6. ajax_set_comment against foreign section is rejected and does not alter other program detail
        other_detail = AJAXSectionDetail()
        other_detail.initialize(other_program, other_sec.id, 'Original', False)
        comment_url = self.ajax_url_base + 'ajax_set_comment'
        r_comment = self.client.post(
            comment_url,
            {'cls': other_sec.id, 'comment': 'Tampered', 'locked': 'yes'},
        )
        self.assertEqual(r_comment.status_code, 200)
        self.assertFalse(json.loads(r_comment.content)['ret'])
        other_detail.refresh_from_db()
        self.assertEqual(other_detail.comment, 'Original')
        self.assertFalse(other_detail.locked)
        self.assertFalse(AJAXSectionDetail.objects.filter(program=self.program, cls_id=other_sec.id).exists())

        # Verify none of the rejected cross-program calls wrote to self.program's changelog
        self.assertEqual(self.changelog.entries.count(), initial_changelog_count)

    def test_invalid_and_missing_inputs_do_not_crash(self):
        """Verify missing, malformed, and out-of-range inputs return JSON errors without HTTP 500."""
        self.clearScheduleAvailability()
        own_sec = self.teachers[0].getTaughtSections(self.program)[0]
        other_sec = self.teachers[1].getTaughtSections(self.program)[0]
        times = list(self.timeslots.order_by('start'))
        room0 = self.rooms[0].identical_resources().filter(event=times[0]).first()
        room1 = self.rooms.exclude(name=room0.name).first().identical_resources().filter(event=times[0]).first()

        # Trailing newlines in block_room_assignments should succeed cleanly
        r_trailing = self.client.post(
            self.schedule_class_url,
            {
                'action': 'assignreg',
                'cls': own_sec.id,
                'block_room_assignments': '\n'.join(
                    f'{ts.id},{room0.identical_id()}' for ts in times[:2]
                ) + '\n\n',
            },
        )
        self.assertEqual(r_trailing.status_code, 200)
        self.assertTrue(json.loads(r_trailing.content)['ret'])

        # Valid swap should succeed cleanly
        r_swap_ok = self.client.post(
            self.schedule_class_url,
            {
                'action': 'swap',
                'assignments': json.dumps([
                    {'section': own_sec.id, 'timeslots': [t.id for t in times[2:4]], 'room_id': room1.identical_id()},
                    {'section': other_sec.id, 'timeslots': [t.id for t in times[0:2]], 'room_id': room0.identical_id()},
                ]),
                'override': 'false',
            },
        )
        self.assertEqual(r_swap_ok.status_code, 200)
        self.assertTrue(json.loads(r_swap_ok.content)['ret'])

        bad_ids = [None, '', 'abc', '0', '-1', '999999', '99999999999999999999', '9' * 5000]
        for bad in bad_ids:
            payload_del = {'action': 'deletereg'}
            if bad is not None:
                payload_del['cls'] = bad
            r = self.client.post(self.schedule_class_url, payload_del)
            self.assertEqual(r.status_code, 200)
            self.assertFalse(json.loads(r.content)['ret'])

            payload_assign = {'action': 'assignreg', 'block_room_assignments': f'{times[0].id},{room0.identical_id()}'}
            if bad is not None:
                payload_assign['cls'] = bad
            r = self.client.post(self.schedule_class_url, payload_assign)
            self.assertEqual(r.status_code, 200)
            self.assertFalse(json.loads(r.content)['ret'])

        # Malformed block_room_assignments
        for bad_block in (None, '', 'not_a_pair', 'abc,123', '123,abc', f'{times[0].id},99999999999999999999'):
            payload = {'action': 'assignreg', 'cls': own_sec.id}
            if bad_block is not None:
                payload['block_room_assignments'] = bad_block
            r = self.client.post(self.schedule_class_url, payload)
            self.assertEqual(r.status_code, 200)
            self.assertFalse(json.loads(r.content)['ret'])

        # Malformed swap payloads
        for bad_swap in (
            None,
            '',
            '{bad_json',
            '{}',
            '[123]',
            json.dumps([{'section': 'abc'}]),
            json.dumps([{'section': own_sec.id, 'timeslots': ['abc'], 'room_id': room0.identical_id()}]),
            json.dumps([{'section': own_sec.id, 'timeslots': [times[0].id], 'room_id': 'bad'}]),
        ):
            payload = {'action': 'swap'}
            if bad_swap is not None:
                payload['assignments'] = bad_swap
            r = self.client.post(self.schedule_class_url, payload)
            self.assertEqual(r.status_code, 200)
            self.assertFalse(json.loads(r.content)['ret'])

        # Moderator endpoint invalid/missing inputs
        mod_url = self.ajax_url_base + 'ajax_assign_moderator'
        for bad in bad_ids:
            payload_sec = {'action': 'assignmod', 'mod': self.teachers[0].id}
            if bad is not None:
                payload_sec['sec'] = bad
            r = self.client.post(mod_url, payload_sec)
            self.assertEqual(r.status_code, 200)
            self.assertFalse(json.loads(r.content)['ret'])

            payload_mod = {'action': 'assignmod', 'sec': own_sec.id}
            if bad is not None:
                payload_mod['mod'] = bad
            r = self.client.post(mod_url, payload_mod)
            self.assertEqual(r.status_code, 200)
            self.assertFalse(json.loads(r.content)['ret'])

        r_bad_act = self.client.post(mod_url, {'action': 'unknown'})
        self.assertEqual(r_bad_act.status_code, 200)
        self.assertFalse(json.loads(r_bad_act.content)['ret'])

        # Valid assignmod and removemod
        mod_user = self.teachers[2]
        r_mod_ok = self.client.post(
            mod_url,
            {'action': 'assignmod', 'sec': own_sec.id, 'mod': mod_user.id, 'override': 'true'},
        )
        self.assertEqual(r_mod_ok.status_code, 200)
        self.assertTrue(json.loads(r_mod_ok.content)['ret'])
        self.assertTrue(own_sec.moderators.filter(id=mod_user.id).exists())

        r_mod_rem_ok = self.client.post(
            mod_url,
            {'action': 'removemod', 'sec': own_sec.id, 'mod': mod_user.id},
        )
        self.assertEqual(r_mod_rem_ok.status_code, 200)
        self.assertTrue(json.loads(r_mod_rem_ok.content)['ret'])
        self.assertFalse(own_sec.moderators.filter(id=mod_user.id).exists())

        # Comment endpoint invalid/missing inputs and valid update
        comment_url = self.ajax_url_base + 'ajax_set_comment'
        for bad in bad_ids:
            payload = {'comment': 'hello'}
            if bad is not None:
                payload['cls'] = bad
            r = self.client.post(comment_url, payload)
            self.assertEqual(r.status_code, 200)
            self.assertFalse(json.loads(r.content)['ret'])

        r_comment_ok = self.client.post(
            comment_url,
            {'cls': own_sec.id, 'comment': 'Valid note', 'locked': 'yes'},
        )
        self.assertEqual(r_comment_ok.status_code, 200)
        self.assertTrue(json.loads(r_comment_ok.content)['ret'])
        detail = AJAXSectionDetail.objects.get(program=self.program, cls_id=own_sec.id)
        self.assertEqual(detail.comment, 'Valid note')
        self.assertTrue(detail.locked)

        # Changelog invalid last_fetched_index
        for bad_idx in (None, 'abc', '99999999999999999999'):
            params = {} if bad_idx is None else {'last_fetched_index': bad_idx}
            r_log = self.client.get(self.changelog_url, params)
            self.assertEqual(r_log.status_code, 200)
