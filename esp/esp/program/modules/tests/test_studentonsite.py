from types import SimpleNamespace

from django.test import override_settings

from esp.program.models import ProgramModule, StudentRegistration
from esp.program.modules.handlers.studentonsite import SelfCheckinForm, StudentOnsite
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.users.models import Record

# ProgramFrameworkTest enables every module by default, and some required ones
# (the lottery, the medical form) take over the page for a student who hasn't
# completed them. Only enable what the onsite pages need so these tests
# exercise the onsite views themselves.
ONSITE_MODULES = ['StudentOnsite', 'StudentClassRegModule', 'StudentRegCore']


class StudentOnsiteBaseTest(ProgramFrameworkTest):
    """Shared setup for the StudentOnsite handler tests (no tests of its own)."""

    def setUp(self):
        super().setUp(
            num_students=3, num_teachers=2, classes_per_teacher=1,
            modules=ProgramModule.objects.filter(handler__in=ONSITE_MODULES),
        )
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]
        self.teacher = self.teachers[0]

    def url(self, page):
        return self.program.get_learn_url() + page

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password='password'))


class StudentOnsitePagesTest(StudentOnsiteBaseTest):

    def test_schedule_page_renders_for_student(self):
        self.login(self.student)
        response = self.client.get(self.url('studentonsite'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/studentonsite/schedule.html')
        self.assertEqual(response.context['webapp_page'], 'schedule')
        self.assertEqual(response.context['program'], self.program)
        self.assertFalse(response.context['checked_in'])

    def test_schedule_page_requires_login(self):
        response = self.client.get(self.url('studentonsite'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_schedule_page_rejects_teachers(self):
        self.login(self.teacher)
        response = self.client.get(self.url('studentonsite'))
        self.assertTemplateUsed(response, 'errors/program/notastudent.html')
        self.assertTemplateNotUsed(response, 'program/modules/studentonsite/schedule.html')

    def test_map_page_renders(self):
        self.login(self.student)
        response = self.client.get(self.url('onsitemap'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/studentonsite/map.html')
        self.assertEqual(response.context['webapp_page'], 'map')

    def test_catalog_lists_classes_from_this_program(self):
        self.login(self.student)
        response = self.client.get(self.url('onsitecatalog'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['webapp_page'], 'catalog')
        classes = response.context['classes']
        self.assertTrue(len(classes) > 0)
        for cls in classes:
            self.assertEqual(cls.parent_program, self.program)
        self.assertEqual(response.context['prereg_url'], self.url('onsiteaddclass'))


class StudentSelfCheckinTest(StudentOnsiteBaseTest):

    def test_disabled_by_default_redirects_to_schedule(self):
        self.login(self.student)
        response = self.client.get(self.url('selfcheckin'))
        self.assertRedirects(response, self.url('studentonsite'), fetch_redirect_response=False)

    def set_mode(self, mode):
        Tag.setTag('student_self_checkin', target=self.program, value=mode)

    def checkin_records(self):
        return Record.objects.filter(user=self.student, program=self.program, event__name='attended')

    def test_open_mode_shows_form_prefilled_with_own_code(self):
        self.set_mode('open')
        self.login(self.student)
        response = self.client.get(self.url('selfcheckin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/studentonsite/selfcheckin.html')
        self.assertEqual(response.context['mode'], 'open')
        self.assertFalse(response.context['checked_in'])
        form = response.context['form']
        self.assertEqual(form.fields['code'].initial, self.student.userHash(self.program))

    def test_open_mode_post_checks_student_in(self):
        self.set_mode('open')
        self.login(self.student)
        self.assertFalse(self.checkin_records().exists())
        response = self.client.post(self.url('selfcheckin'), {'code': self.student.userHash(self.program)})
        self.assertRedirects(response, self.url('studentonsite'), fetch_redirect_response=False)
        self.assertEqual(self.checkin_records().count(), 1)
        self.assertTrue(self.program.isCheckedIn(self.student))

    def test_code_mode_rejects_wrong_code(self):
        self.set_mode('code')
        self.login(self.student)
        response = self.client.post(self.url('selfcheckin'), {'code': 'ZZZZZZ'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('code', response.context['form'].errors)
        self.assertFalse(self.checkin_records().exists())
        self.assertFalse(self.program.isCheckedIn(self.student))

    def test_code_mode_accepts_own_code(self):
        self.set_mode('code')
        self.login(self.student)
        response = self.client.post(self.url('selfcheckin'), {'code': self.student.userHash(self.program)})
        self.assertRedirects(response, self.url('studentonsite'), fetch_redirect_response=False)
        self.assertEqual(self.checkin_records().count(), 1)

    def test_checked_in_student_does_not_get_a_second_record(self):
        self.set_mode('open')
        self.login(self.student)
        code = self.student.userHash(self.program)
        self.client.post(self.url('selfcheckin'), {'code': code})
        response = self.client.post(self.url('selfcheckin'), {'code': code})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['checked_in'])
        self.assertEqual(self.checkin_records().count(), 1)


class StudentOnsiteDetailsTest(StudentOnsiteBaseTest):

    def test_details_for_enrolled_section_shows_section_info(self):
        section = self.program.sections().first()
        section.preregister_student(self.student, fast_force_create=True)
        self.login(self.student)
        response = self.client.get(self.url('onsitedetails/%d' % section.id))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/studentonsite/sectioninfo.html')
        self.assertEqual(response.context['section'], section)

    def test_details_for_section_student_is_not_enrolled_in_redirects(self):
        section = self.program.sections().first()
        self.login(self.student)
        response = self.client.get(self.url('onsitedetails/%d' % section.id))
        self.assertRedirects(response, self.url('studentonsite'), fetch_redirect_response=False)

    def test_details_without_section_id_redirects(self):
        self.login(self.student)
        response = self.client.get(self.url('onsitedetails'))
        self.assertRedirects(response, self.url('studentonsite'), fetch_redirect_response=False)

    def test_details_for_unknown_section_redirects(self):
        self.login(self.student)
        response = self.client.get(self.url('onsitedetails/999999'))
        self.assertRedirects(response, self.url('studentonsite'), fetch_redirect_response=False)


class StudentOnsiteCatalogTimeslotTest(StudentOnsiteBaseTest):

    def test_catalog_for_timeslot_sets_timeslot_in_context(self):
        timeslot = self.program.getTimeSlots()[0]
        self.login(self.student)
        response = self.client.get(self.url('onsitecatalog/%d' % timeslot.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['timeslot'], timeslot)
        self.assertIn('checked_in', response.context)

    def test_catalog_with_invalid_timeslot_shows_error_message(self):
        self.login(self.student)
        for extra in ('abc', '999999'):
            response = self.client.get(self.url('onsitecatalog/%s' % extra))
            self.assertIn(b'Please use the links on the schedule page', response.content)


class SelfCheckinFormTest(StudentOnsiteBaseTest):

    def make_form(self, data=None, user=None):
        return SelfCheckinForm(data, program=self.program, user=user or self.student)

    def test_form_requires_program_and_user(self):
        with self.assertRaises(KeyError):
            SelfCheckinForm()

    def test_code_mode_accepts_own_code(self):
        Tag.setTag('student_self_checkin', target=self.program, value='code')
        form = self.make_form({'code': self.student.userHash(self.program)})
        self.assertTrue(form.is_valid())

    def test_code_mode_rejects_wrong_code(self):
        Tag.setTag('student_self_checkin', target=self.program, value='code')
        form = self.make_form({'code': 'ZZZZZZ'})
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)

    def test_code_mode_rejects_another_students_code(self):
        Tag.setTag('student_self_checkin', target=self.program, value='code')
        other_code = self.students[1].userHash(self.program)
        form = self.make_form({'code': other_code})
        self.assertFalse(form.is_valid())

    def test_open_mode_hides_the_code_field_and_prefills_it(self):
        Tag.setTag('student_self_checkin', target=self.program, value='open')
        form = self.make_form()
        self.assertTrue(form.fields['code'].widget.is_hidden)
        self.assertEqual(form.fields['code'].initial, self.student.userHash(self.program))


class StudentOnsiteAddClearClassTest(StudentOnsiteBaseTest):

    def enrolled(self, section, user=None):
        return StudentRegistration.valid_objects().filter(
            section=section, user=user or self.student, relationship__name='Enrolled').exists()

    def add(self, section, **extra):
        data = {'class_id': section.parent_class_id, 'section_id': section.id}
        data.update(extra)
        return self.client.post(self.url('onsiteaddclass'), data)

    def conflicting_sections(self):
        """Two sections of different classes, forced into the same timeslot."""
        sec1, sec2 = list(self.program.sections().order_by('id')[:2])
        slot = sec1.meeting_times.first()
        self.assertIsNotNone(slot)
        sec2.clear_meeting_times()
        sec2.assign_start_time(slot)
        return sec1, sec2, slot

    def test_add_class_registers_student_and_redirects(self):
        section = self.program.sections().first()
        self.login(self.student)
        response = self.add(section)
        self.assertRedirects(response, self.url('studentonsite'), fetch_redirect_response=False)
        self.assertTrue(self.enrolled(section))

    def test_add_class_without_ids_shows_error_and_registers_nothing(self):
        self.login(self.student)
        response = self.client.post(self.url('onsiteaddclass'), {})
        self.assertIn(b'lost track of your chosen class', response.content)
        self.assertFalse(StudentRegistration.valid_objects().filter(user=self.student).exists())

    def test_add_class_requires_login(self):
        section = self.program.sections().first()
        response = self.add(section)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_add_class_rejects_teachers(self):
        section = self.program.sections().first()
        self.login(self.teacher)
        response = self.add(section)
        self.assertTemplateUsed(response, 'errors/program/notastudent.html')
        self.assertFalse(StudentRegistration.valid_objects().filter(section=section).exists())

    def test_add_class_with_mismatched_class_and_section_is_404(self):
        sec1, sec2 = list(self.program.sections().order_by('id')[:2])
        self.login(self.student)
        response = self.client.post(self.url('onsiteaddclass'),
                                    {'class_id': sec2.parent_class_id, 'section_id': sec1.id})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.enrolled(sec1))

    def test_conflicting_class_asks_for_confirmation(self):
        sec1, sec2, slot = self.conflicting_sections()
        sec1.preregister_student(self.student, fast_force_create=True)
        self.login(self.student)
        response = self.add(sec2)
        self.assertTemplateUsed(response, 'program/modules/studentonsite/conflict_confirm.html')
        self.assertEqual(response.context['section_id'], str(sec2.id))
        self.assertIn('conflicts with your schedule', response.context['confirm_msg'])
        self.assertTrue(self.enrolled(sec1))
        self.assertFalse(self.enrolled(sec2))

    def test_force_replace_swaps_the_conflicting_class(self):
        sec1, sec2, slot = self.conflicting_sections()
        sec1.preregister_student(self.student, fast_force_create=True)
        self.login(self.student)
        response = self.add(sec2, force_replace='true')
        self.assertRedirects(response, self.url('studentonsite'), fetch_redirect_response=False)
        self.assertFalse(self.enrolled(sec1))
        self.assertTrue(self.enrolled(sec2))

    def test_clear_slot_removes_the_class_in_that_timeslot(self):
        section = self.program.sections().first()
        slot = section.meeting_times.first()
        section.preregister_student(self.student, fast_force_create=True)
        self.assertTrue(self.enrolled(section))
        self.login(self.student)
        response = self.client.get(self.url('onsiteclearslot/%d' % slot.id))
        self.assertRedirects(response, self.url('studentonsite'), fetch_redirect_response=False)
        self.assertFalse(self.enrolled(section))

    def test_clear_slot_with_nothing_enrolled_just_redirects(self):
        section = self.program.sections().first()
        slot = section.meeting_times.first()
        self.login(self.student)
        response = self.client.get(self.url('onsiteclearslot/%d' % slot.id))
        self.assertRedirects(response, self.url('studentonsite'), fetch_redirect_response=False)


class StudentOnsiteGradeRangeTest(StudentOnsiteBaseTest):

    def make_student_out_of_grade(self):
        self.program.grade_min = 11
        self.program.grade_max = 12
        self.program.save()
        self.assertLess(self.student.getGrade(self.program), self.program.grade_min)

    def test_student_outside_grade_range_is_rejected(self):
        self.make_student_out_of_grade()
        self.login(self.student)
        response = self.client.get(self.url('studentonsite'))
        self.assertTemplateUsed(response, 'errors/program/wronggrade.html')
        self.assertTemplateNotUsed(response, 'program/modules/studentonsite/schedule.html')

    def test_student_outside_grade_range_cannot_add_a_class(self):
        section = self.program.sections().first()
        self.make_student_out_of_grade()
        self.login(self.student)
        response = self.client.post(self.url('onsiteaddclass'),
                                    {'class_id': section.parent_class_id, 'section_id': section.id})
        self.assertTemplateUsed(response, 'errors/program/wronggrade.html')
        self.assertFalse(StudentRegistration.valid_objects().filter(user=self.student).exists())


class StudentOnsiteContextTest(StudentOnsiteBaseTest):

    def context(self):
        request = SimpleNamespace(user=self.student)
        return StudentOnsite.onsitecontext(request, 'learn', 'TestProgram', '2222_Summer', self.program)

    def test_context_has_basic_values(self):
        context = self.context()
        self.assertEqual(context['user'], self.student)
        self.assertEqual(context['program'], self.program)
        self.assertEqual(context['one'], 'TestProgram')
        self.assertEqual(context['two'], '2222_Summer')

    def test_context_flags_program_without_surveys(self):
        self.assertEqual(self.context()['survey_status'], 'none')

    def test_map_tab_needs_both_an_api_key_and_a_program_center(self):
        Tag.setTag('program_center', target=self.program, value='42.36,-71.09')
        with override_settings(GOOGLE_MAPS_EMBED_KEY=''):
            self.assertFalse(self.context()['map_tab'])
        with override_settings(GOOGLE_MAPS_EMBED_KEY='test-key'):
            self.assertTrue(self.context()['map_tab'])
        Tag.unSetTag('program_center', target=self.program)
        with override_settings(GOOGLE_MAPS_EMBED_KEY='test-key'):
            self.assertFalse(self.context()['map_tab'])

    def test_schedule_page_shows_checked_in_after_self_checkin(self):
        Tag.setTag('student_self_checkin', target=self.program, value='open')
        self.login(self.student)
        self.client.post(self.url('selfcheckin'), {'code': self.student.userHash(self.program)})
        response = self.client.get(self.url('studentonsite'))
        self.assertTrue(response.context['checked_in'])
