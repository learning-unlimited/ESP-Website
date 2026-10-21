from decimal import Decimal
import json

from django.test import RequestFactory

from esp.middleware.threadlocalrequest import ThreadLocals, clear_current_request
from esp.program.models import ClassCategories, ModeratorRecord, ProgramModule
from esp.program.modules.admin_search import SEARCH_CATEGORY_CLASSES
from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.handlers.schedulingcheckmodule import (
    JSONFormatter,
    RawSCFormatter,
    SchedulingCheckModule,
    SchedulingCheckRunner,
)
from esp.program.tests import ProgramFrameworkTest
from esp.resources.models import (
    Resource,
    ResourceAssignment,
    ResourceRequest,
    ResourceType,
)
from esp.tagdict.models import Tag
from esp.tests.factories import make_class as _make_class


class SchedulingCheckHelpersTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 2,
            'num_rooms': 3,
            'num_teachers': 2,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
        })
        super().setUp(*args, **kwargs)

    def tearDown(self):
        clear_current_request()
        super().tearDown()

    def test_json_formatter_format_table_with_list_input(self):
        formatter = JSONFormatter()
        data = [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}]
        result = formatter.format_table(data, {'headings': ['a', 'b']}, help_text='hi')

        parsed = json.loads(result)
        self.assertEqual(parsed['help_text'], 'hi')
        self.assertEqual(parsed['headings'], ['a', 'b'])
        self.assertEqual(parsed['body'], [[1, 2], [3, 4]])

    def test_json_formatter_format_table_with_dict_input(self):
        formatter = JSONFormatter()
        data = {'x': {'a': 10, 'b': 20}, 'y': {'a': 30, 'b': 40}}
        result = formatter.format_table(data, {'headings': ['a', 'b']}, help_text='ok')

        parsed = json.loads(result)
        self.assertEqual(parsed['help_text'], 'ok')
        self.assertEqual(parsed['headings'], ['', 'a', 'b'])
        self.assertEqual(parsed['body'][0][0], 'x')
        self.assertEqual(parsed['body'][1][0], 'y')

    def test_json_formatter_format_list(self):
        formatter = JSONFormatter()
        input_list = [10, 20, 30]
        result = formatter.format_list(input_list, ['value'], help_text='list')

        parsed = json.loads(result)
        self.assertEqual(parsed['help_text'], 'list')
        self.assertEqual(parsed['headings'], ['value'])
        self.assertEqual(parsed['body'], [[10], [20], [30]])

    def test_json_formatter_table_row_with_nested_list_and_int(self):
        formatter = JSONFormatter()
        row = formatter._table_row([['val1', 'val2'], 99, 'string_val'])
        self.assertEqual(row, ["['val1', 'val2']", 99, 'string_val'])

    def test_raw_sc_formatter(self):
        formatter = RawSCFormatter()
        table_data = [{'col': 'value'}]
        list_data = ['item1', 'item2']
        self.assertEqual(formatter.format_table(table_data), table_data)
        self.assertEqual(formatter.format_list(list_data), list_data)

    def test_scheduling_check_runner_respects_unreviewed_get_flag(self):
        request = RequestFactory().get('/manage/%s/scheduling_checks' % self.program.getUrlBase(), {'unreviewed': '1'})
        request.user = self.admins[0]
        ThreadLocals(get_response=lambda r: None).process_request(request)

        runner = SchedulingCheckRunner(self.program)
        self.assertTrue(runner.incl_unreview)

    def test_scheduling_checks_extra_key_returns_diagnostic_output(self):
        request = RequestFactory().get('/manage/%s/scheduling_checks' % self.program.getUrlBase())
        request.user = self.admins[0]
        request.session = {}
        ThreadLocals(get_response=lambda r: None).process_request(request)

        pm = ProgramModule.objects.get(handler='SchedulingCheckModule')
        moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        moduleobj.program = self.program

        response = moduleobj.scheduling_checks(request, 'manage', None, None, None, 'lunch_blocks_setup', self.program)

        self.assertEqual(response.status_code, 200)

        parsed = json.loads(response.content.decode('utf-8'))
        # Verify that the extra diagnostic key returns structured JSON output
        self.assertIn('headings', parsed)
        # The "lunch_blocks_setup" diagnostic should include a "Lunch Blocks" heading
        self.assertIn('Lunch Blocks', parsed['headings'])


class SchedulingCheckModuleViewTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 2,
            'num_rooms': 3,
            'num_teachers': 2,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
        })
        super().setUp(*args, **kwargs)

    def tearDown(self):
        clear_current_request()
        super().tearDown()

    def test_module_properties(self):
        props = SchedulingCheckModule.module_properties()
        self.assertEqual(props['admin_title'], 'Scheduling Diagnostics')
        self.assertEqual(props['link_title'], 'Run Scheduling Diagnostics')
        self.assertEqual(props['module_type'], 'manage')
        self.assertEqual(props['seq'], 10)
        self.assertEqual(props['choosable'], 1)

    def test_get_admin_search_entry(self):
        pm = ProgramModule.objects.get(handler='SchedulingCheckModule')
        moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)

        entry = moduleobj.get_admin_search_entry(self.program, 'manage', 'scheduling_checks', moduleobj)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.id, 'manage_scheduling_checks')
        self.assertEqual(entry.url, '/manage/%s/scheduling_checks' % self.program.getUrlBase())
        self.assertEqual(entry.title, 'Scheduling Diagnostics')
        self.assertEqual(entry.category, SEARCH_CATEGORY_CLASSES)
        self.assertIn('scheduling', entry.keywords)
        self.assertIn('diagnostics', entry.keywords)
        self.assertIn('checks', entry.keywords)

        # Non-matching view name returns None
        self.assertIsNone(moduleobj.get_admin_search_entry(self.program, 'manage', 'other_view', moduleobj))

    def test_is_step(self):
        pm = ProgramModule.objects.get(handler='SchedulingCheckModule')
        moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.assertFalse(moduleobj.isStep())

    def test_scheduling_checks_main_view_renders_html(self):
        request = RequestFactory().get('/manage/%s/scheduling_checks' % self.program.getUrlBase())
        request.user = self.admins[0]
        request.session = {}
        ThreadLocals(get_response=lambda r: None).process_request(request)

        pm = ProgramModule.objects.get(handler='SchedulingCheckModule')
        moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        moduleobj.program = self.program

        response = moduleobj.scheduling_checks(request, 'manage', None, None, None, None, self.program)
        self.assertEqual(response.status_code, 200)
        if hasattr(response, 'render'):
            response.render()
        self.assertIn(b'Schedule Diagnostic Output', response.content)

    def test_scheduling_checks_unreviewed_flag_in_template_context(self):
        request = RequestFactory().get('/manage/%s/scheduling_checks' % self.program.getUrlBase(), {'unreviewed': '1'})
        request.user = self.admins[0]
        request.session = {}
        ThreadLocals(get_response=lambda r: None).process_request(request)

        pm = ProgramModule.objects.get(handler='SchedulingCheckModule')
        moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        moduleobj.program = self.program

        response = moduleobj.scheduling_checks(request, 'manage', None, None, None, None, self.program)
        self.assertEqual(response.status_code, 200)
        if hasattr(response, 'render'):
            response.render()
        self.assertTrue(response.context_data['unreviewed'])
        self.assertIn(b'Exclude unreviewed classes', response.content)

    def test_scheduling_checks_requires_admin(self):
        request = RequestFactory().get('/manage/%s/scheduling_checks' % self.program.getUrlBase())
        request.user = self.students[0]
        request.session = {}
        ThreadLocals(get_response=lambda r: None).process_request(request)

        pm = ProgramModule.objects.get(handler='SchedulingCheckModule')
        moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        moduleobj.program = self.program

        response = moduleobj.scheduling_checks(request, 'manage', None, None, None, None, self.program)
        self.assertEqual(response.status_code, 200)
        if hasattr(response, 'render'):
            response.render()
        self.assertIn(b'you are not an administrator of this program', response.content)


class SchedulingCheckDiagnosticsTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3,
            'num_rooms': 4,
            'num_teachers': 4,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
        })
        super().setUp(*args, **kwargs)

        request = RequestFactory().get('/manage/%s/scheduling_checks' % self.program.getUrlBase())
        request.user = self.admins[0]
        ThreadLocals(get_response=lambda r: None).process_request(request)

        self.timeslots = list(self.program.getTimeSlots().order_by('start'))

    def tearDown(self):
        clear_current_request()
        super().tearDown()

    def _room(self, name, timeslot):
        return Resource.objects.get(name=name, event=timeslot)

    def _schedule_section(self, section, timeslot, room_name, moderators=None):
        section.clearRooms()
        section.clear_meeting_times()
        section.assign_meeting_times([timeslot])
        section.assign_room(self._room(room_name, timeslot))
        if moderators is not None:
            section.moderators.set(moderators)

    def test_all_diagnostics_and_run_diagnostics(self):
        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        diags = runner.all_diagnostics()
        diag_keys = [d[0] for d in diags]
        self.assertIn('lunch_blocks_setup', diag_keys)
        self.assertIn('incompletely_scheduled_classes', diag_keys)
        self.assertIn('room_capacity_mismatch', diag_keys)
        self.assertIn('teachers_teaching_two_classes_same_time', diag_keys)
        self.assertIn('classes_by_category', diag_keys)

        res = runner.run_diagnostics(['lunch_blocks_setup'])
        self.assertEqual(len(res), 1)

    def test_all_diagnostics_with_teacher_moderator_module(self):
        mod_module = ProgramModule.objects.get(handler='TeacherModeratorModule')
        self.program.program_modules.add(mod_module)
        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        diags = runner.all_diagnostics()
        diag_keys = [d[0] for d in diags]
        self.assertIn('unavailable_moderators', diag_keys)
        self.assertIn('mismatched_moderators', diag_keys)
        self.assertIn('moderator_movement_dependency_loops', diag_keys)

    def test_lunch_blocks_setup_and_classes_which_cover_lunch(self):
        lunch_cat, _ = ClassCategories.objects.get_or_create(category='Lunch', is_lunch=True)
        lunch_class = _make_class(
            program=self.program,
            teacher=self.teachers[0],
            title='Lunch Class',
            category=lunch_cat,
            accept=True,
        )
        lunch_sec = lunch_class.get_sections()[0]
        lunch_sec.assign_meeting_times([self.timeslots[0]])
        lunch_sec.assign_room(self._room('Room 0', self.timeslots[0]))

        sec = self.program.sections().exclude(id=lunch_sec.id).first()
        self._schedule_section(sec, self.timeslots[0], 'Room 1')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        lunch_output = runner.lunch_blocks_setup()
        self.assertTrue(len(lunch_output) > 0)

        covering_lunch = runner.classes_which_cover_lunch()
        self.assertIn(sec, covering_lunch)

    def test_incompletely_scheduled_classes_mismatched_room_count(self):
        sec = self.program.sections().first()
        sec.clearRooms()
        sec.clear_meeting_times()
        sec.assign_meeting_times([self.timeslots[0], self.timeslots[1]])
        sec.assignClassRoom(self._room('Room 0', self.timeslots[0]))

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        incompleted = runner.incompletely_scheduled_classes()
        self.assertIn(sec, incompleted)

    def test_incompletely_scheduled_classes_non_contiguous(self):
        sec = self.program.sections().first()
        sec.clearRooms()
        sec.clear_meeting_times()
        sec.assign_meeting_times([self.timeslots[0], self.timeslots[2]])
        sec.assignClassRoom(self._room('Room 0', self.timeslots[0]))
        sec.assignClassRoom(self._room('Room 0', self.timeslots[2]))

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        incompleted = runner.incompletely_scheduled_classes()
        self.assertIn(sec, incompleted)

    def test_inconsistent_rooms_and_times(self):
        sec = self.program.sections().first()
        sec.clearRooms()
        sec.clear_meeting_times()
        sec.assign_meeting_times([self.timeslots[1]])
        sec.assignClassRoom(self._room('Room 0', self.timeslots[0]))

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        inconsistent = runner.inconsistent_rooms_and_times()
        self.assertTrue(any(row['Section'] == sec for row in inconsistent))

    def test_classes_wrong_length(self):
        sec = self.program.sections().first()
        sec.duration = Decimal('2.0')
        sec.save()
        self._schedule_section(sec, self.timeslots[0], 'Room 0')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        wrong_length = runner.classes_wrong_length()
        self.assertIn(sec, wrong_length)

    def test_unapproved_scheduled_classes(self):
        sec = self.program.sections().first()
        sec.status = 5
        sec.save()
        self._schedule_section(sec, self.timeslots[0], 'Room 0')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        unapproved = runner.unapproved_scheduled_classes()
        self.assertIn(sec, unapproved)

    def test_teachers_teaching_two_classes_same_time(self):
        sections = list(self.program.sections()[:2])
        teacher = self.teachers[0]
        sections[0].parent_class.teachers.set([teacher])
        sections[1].parent_class.teachers.set([teacher])

        self._schedule_section(sections[0], self.timeslots[0], 'Room 0')
        self._schedule_section(sections[1], self.timeslots[0], 'Room 1')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        conflicts = runner.teachers_teaching_two_classes_same_time()
        self.assertTrue(any(row['Username'] == teacher and row['Timeslot'] == self.timeslots[0] for row in conflicts))

    def test_teachers_teaching_two_classes_with_moderator_module(self):
        mod_module = ProgramModule.objects.get(handler='TeacherModeratorModule')
        self.program.program_modules.add(mod_module)

        sections = list(self.program.sections()[:2])
        user = self.teachers[0]
        sections[0].parent_class.teachers.set([user])
        sections[1].moderators.set([user])

        self._schedule_section(sections[0], self.timeslots[0], 'Room 0')
        self._schedule_section(sections[1], self.timeslots[0], 'Room 1', moderators=[user])

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        conflicts = runner.teachers_teaching_two_classes_same_time()
        self.assertTrue(any(row['Username'] == user for row in conflicts))

    def test_multiple_classes_same_resource_same_time(self):
        sections = list(self.program.sections()[:2])
        self._schedule_section(sections[0], self.timeslots[0], 'Room 0')
        sections[1].clearRooms()
        sections[1].clear_meeting_times()
        sections[1].assign_meeting_times([self.timeslots[0]])
        ResourceAssignment.objects.create(
            target=sections[1],
            resource=self._room('Room 0', self.timeslots[0]),
        )

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        conflicts = runner.multiple_classes_same_resource_same_time()
        self.assertTrue(len(conflicts) > 0)
        self.assertEqual(conflicts[0]['Resource'], self._room('Room 0', self.timeslots[0]))

    def test_room_capacity_mismatch(self):
        sec = self.program.sections().first()
        sec.parent_class.class_size_max = 50
        sec.parent_class.save()

        room = self._room('Room 0', self.timeslots[0])
        room.num_students = 10
        room.save()

        self._schedule_section(sec, self.timeslots[0], 'Room 0')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        mismatches = runner.room_capacity_mismatch()
        self.assertTrue(any(row['Section'] == str(sec) for row in mismatches))

    def test_hungry_teachers(self):
        lunch_cat, _ = ClassCategories.objects.get_or_create(category='Lunch', is_lunch=True)
        lunch_class = _make_class(
            program=self.program,
            teacher=self.teachers[0],
            title='Lunch Class',
            category=lunch_cat,
            accept=True,
        )
        lunch_sec = lunch_class.get_sections()[0]
        lunch_sec.assign_meeting_times([self.timeslots[0]])
        lunch_sec.assign_room(self._room('Room 0', self.timeslots[0]))

        teacher = self.teachers[1]
        sec = self.program.sections().filter(parent_class__category__is_lunch=False).first()
        sec.parent_class.teachers.set([teacher])
        self._schedule_section(sec, self.timeslots[0], 'Room 1')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        hungry = runner.hungry_teachers(ignore_open_classes=True)
        self.assertTrue(any(row['Username'] == teacher for row in hungry))

    def test_classes_and_capacity_by_category(self):
        sections = list(self.program.sections()[:2])
        self._schedule_section(sections[0], self.timeslots[0], 'Room 0')
        self._schedule_section(sections[1], self.timeslots[0], 'Room 1')

        external_cat, _ = ClassCategories.objects.get_or_create(category='External Cat')
        external_class = _make_class(
            program=self.program,
            teacher=self.teachers[2],
            title='External Class',
            category=external_cat,
            accept=True,
        )
        ext_sec = external_class.get_sections()[0]
        self._schedule_section(ext_sec, self.timeslots[0], 'Room 2')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        classes_data = runner.classes_by_category()
        capacity_data = runner.capacity_by_category()

        self.assertIn(self.timeslots[0], classes_data)
        self.assertIn(self.timeslots[0], capacity_data)
        self.assertGreater(classes_data[self.timeslots[0]][external_cat.category], 0)

    def test_classes_and_capacity_by_grade(self):
        sec = self.program.sections().first()
        sec.parent_class.grade_min = 7
        sec.parent_class.grade_max = 9
        sec.parent_class.save()
        self._schedule_section(sec, self.timeslots[0], 'Room 0')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        classes_by_grade = runner.classes_by_grade()
        capacity_by_grade = runner.capacity_by_grade()

        self.assertIn(self.timeslots[0], classes_by_grade)
        self.assertIn(self.timeslots[0], capacity_by_grade)
        self.assertGreaterEqual(classes_by_grade[self.timeslots[0]][7], 1)

    def test_admins_teaching_per_timeblock(self):
        sec = self.program.sections().first()
        sec.parent_class.teachers.set([self.admins[0]])
        self._schedule_section(sec, self.timeslots[0], 'Room 0')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        data = runner.admins_teaching_per_timeblock()
        self.assertIn(self.timeslots[0], data)
        self.assertEqual(data[self.timeslots[0]]['Number'], 1)
        self.assertIn(self.admins[0].name(), data[self.timeslots[0]]['Admin Names'])

    def test_wrong_classroom_type_and_missing_resources(self):
        sec = self.program.sections().first()
        self._schedule_section(sec, self.timeslots[0], 'Room 0')

        classroom_space_type, _ = ResourceType.objects.get_or_create(
            name='Classroom space',
            program=self.program,
            defaults={'description': 'Classroom space'},
        )
        ResourceRequest.objects.create(
            desired_value='Auditorium',
            res_type=classroom_space_type,
            target=sec,
        )

        projector_type, _ = ResourceType.objects.get_or_create(
            name='Projector',
            program=self.program,
            defaults={'description': 'Projector'},
        )
        ResourceRequest.objects.create(
            desired_value='HD Projector',
            res_type=projector_type,
            target=sec,
        )

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        wrong_types = runner.wrong_classroom_type()
        self.assertTrue(any(row['Section'] == sec and row['Requested Type'] == 'Auditorium' for row in wrong_types))

        missing_res = runner.classes_missing_resources()
        self.assertTrue(any(row['Section'] == sec for row in missing_res))

        by_hour = runner.missing_resources_by_hour()
        self.assertTrue(any(row['Timeblock'] == self.timeslots[0] for row in by_hour))

    def test_teachers_unavailable(self):
        teacher = self.teachers[0]
        teacher.clearAvailableTimes(self.program)

        sec = self.program.sections().first()
        sec.parent_class.teachers.set([teacher])
        self._schedule_section(sec, self.timeslots[0], 'Room 0')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        unavailable = runner.teachers_unavailable()
        self.assertTrue(any(row['Teacher'] == teacher and row['Time'] == self.timeslots[0] for row in unavailable))

    def test_teachers_who_like_running(self):
        teacher = self.teachers[0]
        sections = list(self.program.sections()[:2])
        sections[0].parent_class.teachers.set([teacher])
        sections[1].parent_class.teachers.set([teacher])

        self._schedule_section(sections[0], self.timeslots[0], 'Room 0')
        self._schedule_section(sections[1], self.timeslots[1], 'Room 1')

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        runners = runner.teachers_who_like_running()
        self.assertTrue(any(row['Username'] == teacher and row['Room 1'].name == 'Room 0' and row['Room 2'].name == 'Room 1' for row in runners))

    def test_no_overlap_classes(self):
        classes = list(self.program.classes()[:2])
        sec0 = classes[0].get_sections()[0]
        sec1 = classes[1].get_sections()[0]
        self._schedule_section(sec0, self.timeslots[0], 'Room 0')
        self._schedule_section(sec1, self.timeslots[0], 'Room 1')

        Tag.setTag(
            'no_overlap_classes',
            target=self.program,
            value=json.dumps({'Overlap Check': [classes[0].id, classes[1].id]}),
        )

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        overlaps = runner.no_overlap_classes()
        self.assertTrue(any(row['Comment'] == 'Overlap Check' for row in overlaps))

    def test_special_classroom_types(self):
        sec = self.program.sections().first()
        self._schedule_section(sec, self.timeslots[0], 'Room 0')

        comp_type, _ = ResourceType.objects.get_or_create(
            name='Computer Lab',
            program=self.program,
            defaults={'description': 'Computer Lab'},
        )
        ResourceRequest.objects.create(
            desired_value='computer cluster',
            res_type=comp_type,
            target=sec,
        )

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        special = runner.special_classroom_types()
        self.assertTrue(any(row['Class Section'] == sec for row in special))

    def test_inflexible_teachers(self):
        teacher = self.teachers[0]
        teacher.clearAvailableTimes(self.program)

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        inflexible = runner.inflexible_teachers()
        self.assertTrue(any(row['Username'] == teacher.username for row in inflexible))

    def test_unavailable_and_mismatched_moderators(self):
        mod_module = ProgramModule.objects.get(handler='TeacherModeratorModule')
        self.program.program_modules.add(mod_module)

        moderator = self.teachers[1]
        moderator.clearAvailableTimes(self.program)

        sec = self.program.sections().first()
        self._schedule_section(sec, self.timeslots[0], 'Room 0', moderators=[moderator])

        runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        unavail = runner.unavailable_moderators()
        self.assertTrue(any(row['Section'] == sec for row in unavail))

        mismatched = runner.mismatched_moderators()
        self.assertTrue(any(row['Section'] == sec for row in mismatched))
