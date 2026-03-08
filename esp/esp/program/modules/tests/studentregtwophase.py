"""
Tests for the StudentRegTwoPhase module, specifically the confirmation
button (#1166) and minimum class requirement (#2535) features.
"""

import random

from django.core import mail

from esp.program.models import RegistrationType, StudentRegistration, StudentSubjectInterest
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.users.models import Record, RecordType


class StudentRegTwoPhaseTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        # Set up the program with enough timeslots, teachers, rooms, and classes
        kwargs.update({
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 6, 'classes_per_teacher': 1, 'sections_per_class': 1,
            'num_rooms': 6,
        })
        super().setUp(*args, **kwargs)

        self.schedule_randomly()

        # Set required tags for TwoPhase module
        Tag.objects.get_or_create(
            key='num_stars', value='3',
            content_type=self.program_content_type,
            object_id=self.program.id
        )

        # Make all modules non-required so we don't hit required page redirects
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        # Ensure the twophase_reg_done RecordType exists
        RecordType.objects.get_or_create(name='twophase_reg_done')

    @property
    def program_content_type(self):
        from django.contrib.contenttypes.models import ContentType
        return ContentType.objects.get_for_model(self.program)

    def _star_classes(self, student, num_classes):
        """Helper: star a number of classes for a student."""
        classes = list(self.program.classes())[:num_classes]
        starred = []
        for cls in classes:
            interest, created = StudentSubjectInterest.objects.get_or_create(
                user=student,
                subject=cls,
            )
            starred.append(cls)
        return starred

    def _set_priorities(self, student, section):
        """Helper: set Priority/1 registration for a student on a section."""
        reg_type, _ = RegistrationType.objects.get_or_create(
            name='Priority/1', category='student')
        StudentRegistration.valid_objects().filter(
            user=student, section=section, relationship=reg_type).delete()
        StudentRegistration.objects.create(
            user=student, section=section, relationship=reg_type)

    # ---------------------------------------------------------------
    # Test: Main registration page loads
    # ---------------------------------------------------------------
    def test_main_page_loads(self):
        """The TwoPhase registration page should load for a logged-in student."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'),
            "Couldn't log in as student %s" % student.username)

        response = self.client.get(
            '/learn/%s/studentreg2phase' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)

    # ---------------------------------------------------------------
    # Test: GET on confirm_registration redirects (must be POST)
    # ---------------------------------------------------------------
    def test_confirm_get_redirects(self):
        """GET to confirm_registration should redirect (only POST allowed)."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        response = self.client.get(
            '/learn/%s/confirm_registration' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 302)

    # ---------------------------------------------------------------
    # Test: Successful confirmation creates Record and sends email
    # ---------------------------------------------------------------
    def test_confirm_success(self):
        """POST to confirm_registration should create a Record and send email."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        # Star some classes
        self._star_classes(student, 3)

        # Clear mail outbox
        mail.outbox = []

        # Confirm
        response = self.client.post(
            '/learn/%s/confirm_registration' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)

        # Check Record was created
        rt = RecordType.objects.get(name='twophase_reg_done')
        self.assertTrue(
            Record.objects.filter(
                user=student, event=rt, program=self.program).exists(),
            "twophase_reg_done Record was not created")

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Lottery Preferences Confirmation', mail.outbox[0].subject)

    # ---------------------------------------------------------------
    # Test: Confirmation page shows starred classes
    # ---------------------------------------------------------------
    def test_confirm_shows_starred_classes(self):
        """Confirmation page should display the student's starred classes."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        starred = self._star_classes(student, 2)

        response = self.client.post(
            '/learn/%s/confirm_registration' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)

        for cls in starred:
            self.assertContains(response, cls.title)

    # ---------------------------------------------------------------
    # Test: Re-confirmation doesn't create duplicate Records
    # ---------------------------------------------------------------
    def test_reconfirm_no_duplicate(self):
        """Confirming twice should not create duplicate Records."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        self._star_classes(student, 3)

        # Confirm twice
        self.client.post(
            '/learn/%s/confirm_registration' % self.program.getUrlBase())
        self.client.post(
            '/learn/%s/confirm_registration' % self.program.getUrlBase())

        rt = RecordType.objects.get(name='twophase_reg_done')
        count = Record.objects.filter(
            user=student, event=rt, program=self.program).count()
        self.assertEqual(count, 1, "Expected 1 Record, got %d" % count)

    # ---------------------------------------------------------------
    # Test: Main page shows confirmed status after confirmation
    # ---------------------------------------------------------------
    def test_main_page_shows_confirmed(self):
        """After confirmation, the main page should show confirmed status."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        self._star_classes(student, 3)

        # Confirm
        self.client.post(
            '/learn/%s/confirm_registration' % self.program.getUrlBase())

        # Go back to main page
        response = self.client.get(
            '/learn/%s/studentreg2phase' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Send Me a Confirmation Email')

    # ---------------------------------------------------------------
    # Tests: Minimum class requirement (twophase_min_classes tag)
    # ---------------------------------------------------------------
    def test_min_classes_rejects(self):
        """With min_classes set, confirmation should be rejected if too few classes starred."""
        Tag.objects.get_or_create(
            key='twophase_min_classes', value='5',
            content_type=self.program_content_type,
            object_id=self.program.id
        )

        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        self._star_classes(student, 2)

        response = self.client.post(
            '/learn/%s/confirm_registration' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 302,
                         "Expected redirect when below min_classes")

        # Check error message was set
        from django.contrib.messages import get_messages
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('must star at least 5 classes', str(messages[0]))

        rt = RecordType.objects.get(name='twophase_reg_done')
        self.assertFalse(
            Record.objects.filter(
                user=student, event=rt, program=self.program).exists(),
            "Record should not be created when below min_classes")

    def test_min_classes_passes(self):
        """With min_classes set, confirmation should succeed when enough classes starred."""
        Tag.objects.get_or_create(
            key='twophase_min_classes', value='2',
            content_type=self.program_content_type,
            object_id=self.program.id
        )

        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        self._star_classes(student, 3)

        response = self.client.post(
            '/learn/%s/confirm_registration' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)

        rt = RecordType.objects.get(name='twophase_reg_done')
        self.assertTrue(
            Record.objects.filter(
                user=student, event=rt, program=self.program).exists(),
            "Record should be created when at/above min_classes")

    def test_no_min_classes_no_restriction(self):
        """Without twophase_min_classes tag, any number of classes should work."""
        Tag.objects.filter(key='twophase_min_classes').delete()

        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        self._star_classes(student, 1)

        response = self.client.post(
            '/learn/%s/confirm_registration' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)

        rt = RecordType.objects.get(name='twophase_reg_done')
        self.assertTrue(
            Record.objects.filter(
                user=student, event=rt, program=self.program).exists())

    def test_min_classes_zero_no_restriction(self):
        """twophase_min_classes=0 should behave like no restriction."""
        Tag.objects.get_or_create(
            key='twophase_min_classes', value='0',
            content_type=self.program_content_type,
            object_id=self.program.id
        )

        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        self._star_classes(student, 1)

        response = self.client.post(
            '/learn/%s/confirm_registration' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)

    def test_main_page_shows_min_classes(self):
        """When min_classes is set, the main page should show the requirement."""
        Tag.objects.get_or_create(
            key='twophase_min_classes', value='3',
            content_type=self.program_content_type,
            object_id=self.program.id
        )

        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        response = self.client.get(
            '/learn/%s/studentreg2phase' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You must star at least 3 classes')

    # ---------------------------------------------------------------
    # Tests: Mark classes page and AJAX endpoints
    # ---------------------------------------------------------------
    def test_mark_classes_page_loads(self):
        """The mark_classes page should load for a logged-in student."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        response = self.client.get(
            '/learn/%s/mark_classes' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)

    def test_mark_classes_interested_saves(self):
        """POST to mark_classes_interested should save student interests."""
        import json as json_module
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        grade = student.getGrade(self.program)
        classes = list(self.program.classes().filter(
            status__gte=0,
            grade_min__lte=grade,
            grade_max__gte=grade
        ))[:2]
        class_ids = [c.id for c in classes]

        response = self.client.post(
            '/learn/%s/mark_classes_interested' % self.program.getUrlBase(),
            {'json_data': json_module.dumps({
                'interested': class_ids,
                'not_interested': []
            })},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        for cls in classes:
            self.assertTrue(
                StudentSubjectInterest.objects.filter(
                    user=student, subject=cls).exists(),
                "SSI should be created for class %s" % cls.id)

    def test_mark_classes_interested_removes(self):
        """POST to mark_classes_interested should remove interests."""
        import json as json_module
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        starred = self._star_classes(student, 2)

        class_ids = [c.id for c in starred]
        response = self.client.post(
            '/learn/%s/mark_classes_interested' % self.program.getUrlBase(),
            {'json_data': json_module.dumps({
                'interested': [],
                'not_interested': class_ids
            })},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        for cls in starred:
            ssi = StudentSubjectInterest.objects.filter(
                user=student, subject=cls).first()
            self.assertIsNotNone(ssi.end_date,
                                 "SSI should have end_date set")

    def test_mark_classes_interested_bad_json(self):
        """Bad JSON to mark_classes_interested should return 400."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        response = self.client.post(
            '/learn/%s/mark_classes_interested' % self.program.getUrlBase(),
            {'json_data': 'not valid json'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)

    def test_mark_classes_interested_missing_data(self):
        """Missing json_data in mark_classes_interested should return 400."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        response = self.client.post(
            '/learn/%s/mark_classes_interested' % self.program.getUrlBase(),
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)

    # ---------------------------------------------------------------
    # Tests: Module helper methods (isCompleted, students, studentDesc)
    # ---------------------------------------------------------------
    def test_is_completed_false_before_confirm(self):
        """isCompleted should return False before confirmation."""
        from esp.program.modules.handlers.studentregtwophase import StudentRegTwoPhase

        student = random.choice(self.students)
        module = StudentRegTwoPhase()
        module.program = self.program
        module.user = student

        self.assertFalse(module.isCompleted())

    def test_is_completed_true_after_confirm(self):
        """isCompleted should return True after confirmation."""
        from esp.program.modules.handlers.studentregtwophase import StudentRegTwoPhase

        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        self._star_classes(student, 2)
        self.client.post(
            '/learn/%s/confirm_registration' % self.program.getUrlBase())

        module = StudentRegTwoPhase()
        module.program = self.program
        module.user = student

        self.assertTrue(module.isCompleted())

    def test_students_method(self):
        """students() method should return correct student sets."""
        from esp.program.modules.handlers.studentregtwophase import StudentRegTwoPhase

        student1 = self.students[0]
        student2 = self.students[1]

        self._star_classes(student1, 2)

        section = list(self.program.sections())[0]
        self._set_priorities(student2, section)

        module = StudentRegTwoPhase()
        module.program = self.program

        students_dict = module.students()

        self.assertIn(student1, students_dict['twophase_star_students'])
        self.assertIn(student2, students_dict['twophase_priority_students'])

    def test_student_desc_method(self):
        """studentDesc() method should return correct descriptions."""
        from esp.program.modules.handlers.studentregtwophase import StudentRegTwoPhase

        module = StudentRegTwoPhase()
        desc = module.studentDesc()

        self.assertIn('twophase_star_students', desc)
        self.assertIn('twophase_priority_students', desc)
        self.assertIn('starred', desc['twophase_star_students'])

    def test_students_method_qobject(self):
        """students() method with QObject=True should return Q objects."""
        from esp.program.modules.handlers.studentregtwophase import StudentRegTwoPhase
        from django.db.models import Q

        student1 = self.students[0]
        self._star_classes(student1, 2)

        module = StudentRegTwoPhase()
        module.program = self.program

        q_dict = module.students(QObject=True)

        self.assertIn('twophase_star_students', q_dict)
        self.assertIn('twophase_priority_students', q_dict)
        self.assertIsInstance(q_dict['twophase_star_students'], Q)
        self.assertIsInstance(q_dict['twophase_priority_students'], Q)

    # ---------------------------------------------------------------
    # Tests: View classes (public catalog) and rank classes pages
    # ---------------------------------------------------------------
    def test_view_classes_page_loads(self):
        """The view_classes page should load without authentication."""
        response = self.client.get(
            '/learn/%s/view_classes' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)

    def test_view_classes_shows_categories(self):
        """The view_classes page should include category filter options."""
        response = self.client.get(
            '/learn/%s/view_classes' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)
        # Category choices should be in context
        self.assertIn('category_choices', response.context)

    def test_rank_classes_page_loads(self):
        """The rank_classes page should load for a logged-in student."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        timeslot = self.program.getTimeSlots()[0]
        response = self.client.get(
            '/learn/%s/rank_classes/%s' % (self.program.getUrlBase(), timeslot.id))
        self.assertEqual(response.status_code, 200)

    def test_rank_classes_invalid_timeslot(self):
        """rank_classes with invalid timeslot should return 404."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        response = self.client.get(
            '/learn/%s/rank_classes/99999' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 404)

    # ---------------------------------------------------------------
    # Tests: Save priorities AJAX endpoint
    # ---------------------------------------------------------------
    def test_save_priorities_success(self):
        """POST to save_priorities should save priority registrations."""
        import json as json_module
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        # Get a timeslot and a class in that timeslot
        timeslot = self.program.getTimeSlots()[0]
        sections = list(self.program.sections().filter(
            meeting_times=timeslot,
            status__gte=0,
            parent_class__status__gte=0
        ))
        if not sections:
            self.skipTest("No sections in first timeslot")
        section = sections[0]

        response = self.client.post(
            '/learn/%s/save_priorities' % self.program.getUrlBase(),
            {'json_data': json_module.dumps({
                str(timeslot.id): {'1': str(section.parent_class.id)}
            })})
        self.assertEqual(response.status_code, 302)

        # Verify the registration was created
        reg_type = RegistrationType.objects.get(name='Priority/1', category='student')
        self.assertTrue(
            StudentRegistration.valid_objects().filter(
                user=student, section=section, relationship=reg_type).exists())

    def test_save_priorities_clear(self):
        """POST to save_priorities with empty should clear priority."""
        import json as json_module
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        # Set up an existing priority
        timeslot = self.program.getTimeSlots()[0]
        sections = list(self.program.sections().filter(
            meeting_times=timeslot, status__gte=0))
        if not sections:
            self.skipTest("No sections in first timeslot")
        section = sections[0]
        self._set_priorities(student, section)

        # Clear the priority
        response = self.client.post(
            '/learn/%s/save_priorities' % self.program.getUrlBase(),
            {'json_data': json_module.dumps({
                str(timeslot.id): {'1': ''}
            })})
        self.assertEqual(response.status_code, 302)

        # Verify the registration was expired
        reg_type = RegistrationType.objects.get(name='Priority/1', category='student')
        self.assertFalse(
            StudentRegistration.valid_objects().filter(
                user=student, section=section, relationship=reg_type).exists())

    def test_save_priorities_bad_json(self):
        """Bad JSON to save_priorities should return 400."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        response = self.client.post(
            '/learn/%s/save_priorities' % self.program.getUrlBase(),
            {'json_data': 'not valid json'})
        self.assertEqual(response.status_code, 400)

    def test_save_priorities_missing_data(self):
        """Missing json_data in save_priorities should return 400."""
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        response = self.client.post(
            '/learn/%s/save_priorities' % self.program.getUrlBase(),
            {})
        self.assertEqual(response.status_code, 400)

    def test_save_priorities_bad_format(self):
        """Mis-formatted json_data in save_priorities should return 400."""
        import json as json_module
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'))

        # Multiple timeslot keys (should be exactly one)
        response = self.client.post(
            '/learn/%s/save_priorities' % self.program.getUrlBase(),
            {'json_data': json_module.dumps({'1': {}, '2': {}})})
        self.assertEqual(response.status_code, 400)

    # ---------------------------------------------------------------
    # Tests: Module properties
    # ---------------------------------------------------------------
    def test_module_properties(self):
        """module_properties() should return expected values."""
        from esp.program.modules.handlers.studentregtwophase import StudentRegTwoPhase

        props = StudentRegTwoPhase.module_properties()

        self.assertEqual(props['module_type'], 'learn')
        self.assertEqual(props['link_title'], 'Two-Phase Student Registration')
        self.assertTrue(props['required'])
