from unittest.mock import patch

from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ProgramModule, ClassSubject, ClassSection, ClassCategories, StudentRegistration
from esp.users.models import Record, RecordType
from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.handlers.studentlunchselection import (
    StudentLunchSelectionForm,
    StudentLunchSelection,
)


class StudentLunchSelectionTest(ProgramFrameworkTest):
    """test written for the solution of studentluchsection.py in modules/handler folder."""

    def setUp(self, *args, **kwargs):
    #   simple setup starting intialilisng everything
        modules = [
            ProgramModule.objects.get(handler='StudentLunchSelection'),
            ProgramModule.objects.get(handler='StudentRegCore'),
        ]
        kwargs.update({'modules': modules})
        super().setUp(*args, **kwargs)

        self.add_student_profiles()

        self.student = self.students[0]
        self.assertTrue(self.client.login(username=self.student.username, password='password'))

        self.lunch_category, _ = ClassCategories.objects.get_or_create(
            category='Lunch',
            defaults={'symbol': 'L'},
        )

        self.lunch_class = ClassSubject.objects.create(
            title='Lunch Block',
            category=self.lunch_category,
            grade_min=7,
            grade_max=12,
            parent_program=self.program,
            class_size_max=50,
            class_info='Lunch period',
        )
        self.lunch_class.accept()
        self.lunch_class.add_section(duration=1.0)
        self.lunch_section = self.lunch_class.get_sections().first()
        self.assertIsNotNone(self.lunch_section) #this is a safety check it can be be removed tho
        self.lunch_event = self.program.getTimeSlots()[0]
        self.lunch_section.assign_start_time(self.lunch_event)
        self.lunch_record_type, _ = RecordType.objects.get_or_create(
            name='lunch_selected',
            defaults={'description': 'Student selected lunch period'},
        )






        pm = ProgramModule.objects.get(handler='StudentLunchSelection')
        self.module_obj = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.module_obj.__class__ = StudentLunchSelection

        self.program_day = self.program.dates()[0]

    def test_is_step_true_when_lunch_event_exists(self):
        self.assertTrue(self.module_obj.isStep())

    def test_is_completed_false_before_record(self):
        self.assertFalse(self.module_obj.isCompleted(user=self.student))

    def test_is_completed_true_after_record(self):
        Record.objects.create(user=self.student, program=self.program, event=self.lunch_record_type)
        self.assertTrue(self.module_obj.isCompleted(user=self.student))

    def test_form_choices_include_timeslot_and_decline_option(self):
        form = StudentLunchSelectionForm(self.program, self.student, self.program_day)
        choices = form.fields['timeslot'].choices

        # Event choice should be present for this day.
        self.assertIn((self.lunch_event.id, self.lunch_event.short_description), choices)
        # Explicit decline option should always be present.
        self.assertIn((-1, 'No lunch period'), choices)

    def test_form_save_registers_valid_selection(self):
        form = StudentLunchSelectionForm(
            self.program,
            self.student,
            self.program_day,
            data={'timeslot': str(self.lunch_event.id)},
        )
        self.assertTrue(form.is_valid())

        result, msg = form.save_data()
        self.assertTrue(result)
        self.assertIn('Registered for', msg)

        self.assertTrue(
            StudentRegistration.valid_objects().filter(
                user=self.student,
                section=self.lunch_section,
            ).exists()
        )

    def test_form_rejects_unknown_timeslot_at_validation(self):
        form = StudentLunchSelectionForm(
            self.program,
            self.student,
            self.program_day,
            data={'timeslot': '999999999'},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('timeslot', form.errors)

    def test_form_save_rejects_blocked_selection(self):
        form = StudentLunchSelectionForm(
            self.program,
            self.student,
            self.program_day,
            data={'timeslot': str(self.lunch_event.id)},
        )
        self.assertTrue(form.is_valid())

        with patch.object(ClassSection, 'cannotAdd', return_value='blocked'):
            result, msg = form.save_data()

        self.assertFalse(result)
        self.assertIn('Failed to register for', msg)

    def test_form_save_decline_clears_existing_lunch_registration(self):
        self.lunch_section.preregister_student(self.student, fast_force_create=True)
        self.assertTrue(
            StudentRegistration.valid_objects().filter(
                user=self.student,
                section=self.lunch_section,
            ).exists()
        )

        form = StudentLunchSelectionForm(
            self.program,
            self.student,
            self.program_day,
            data={'timeslot': '-1'},
        )
        self.assertTrue(form.is_valid())

        result, msg = form.save_data()
        self.assertTrue(result)
        self.assertEqual(msg, 'Lunch period declined.')

        self.assertFalse(
            StudentRegistration.valid_objects().filter(
                user=self.student,
                section=self.lunch_section,
            ).exists()
        )

    def test_select_lunch_page_renders_for_eligible_student(self):
        url = '/learn/%s/select_lunch' % self.program.getUrlBase()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Schedule a lunch period')