"""
Tests for the StudentRegTwoPhase module, specifically the confirmation
button (#1166) and minimum class requirement (#2535) features.
"""

import json
import random
from datetime import datetime

from django.core import mail

from esp.program.class_status import ClassStatus
from esp.program.models import (
    ClassSection,
    ClassSubject,
    RegistrationProfile,
    RegistrationType,
    StudentRegistration,
    StudentSubjectInterest,
)
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.users.models import ContactInfo, ESPUser, Record, RecordType, StudentInfo


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
    # save_priorities: unapproved classes must be skipped (#bugfix)
    # ---------------------------------------------------------------
    LOGGER_NAME = 'esp.program.modules.handlers.studentregtwophase'

    def _ensure_student_profile(self, student):
        """Give student grade/YOG so getGrade() is within program class range."""
        thisyear = ESPUser.program_schoolyear(self.program)
        prof = RegistrationProfile.getLastForProgram(student, self.program)
        prof.program = self.program
        if not prof.contact_user:
            prof.contact_user = ContactInfo.objects.create(
                user=student,
                first_name=student.first_name,
                last_name=student.last_name,
                e_mail=student.email,
            )
        if not prof.student_info:
            prof.student_info = StudentInfo.objects.create(
                user=student,
                graduation_year=ESPUser.YOGFromGrade(10, thisyear),
                dob=datetime(thisyear - 15, 1, 1),
            )
        prof.save()

    def _find_class_and_section_for_timeslot(self, timeslot):
        """Return (ClassSubject, ClassSection) with a meeting in ``timeslot``."""
        for cls in self.program.classes():
            for sec in cls.get_sections():
                times = list(sec.meeting_times.all())
                if not times:
                    continue
                if times[0].start == timeslot.start:
                    return cls, sec
        return None, None

    def _save_priorities_post(self, student, timeslot, class_id):
        self._ensure_student_profile(student)
        self.assertTrue(
            self.client.login(username=student.username, password='password'),
        )
        payload = {str(timeslot.id): {'1': str(class_id)}}
        return self.client.post(
            '/learn/%s/save_priorities' % self.program.getUrlBase(),
            {'json_data': json.dumps(payload)},
        )

    def test_save_priorities_approved_class_creates_priority_registration(self):
        """When section and class are approved, save_priorities records Priority/1."""
        self.schedule_randomly()
        timeslot = None
        cls = None
        sec = None
        for ts in self.timeslots:
            cls, sec = self._find_class_and_section_for_timeslot(ts)
            if cls is not None:
                timeslot = ts
                break
        self.assertIsNotNone(
            cls,
            'Expected at least one class to be scheduled in some timeslot',
        )
        student = self.students[0]

        RegistrationType.objects.get_or_create(name='Priority/1', category='student')
        StudentRegistration.objects.filter(
            user=student,
            relationship__name='Priority/1',
            section__parent_class__parent_program=self.program,
        ).delete()

        self.assertGreater(sec.status, 0)
        self.assertGreater(sec.parent_class.status, 0)

        response = self._save_priorities_post(student, timeslot, cls.id)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            StudentRegistration.valid_objects().filter(
                user=student,
                relationship__name='Priority/1',
                section__parent_class=cls,
            ).exists(),
            'Expected Priority/1 registration for approved class',
        )

    def test_save_priorities_unapproved_class_skipped_and_warns(self):
        """Unapproved section/class must not get a priority registration; log warning."""
        self.schedule_randomly()
        timeslot = self.timeslots[0]
        cls, sec = self._find_class_and_section_for_timeslot(timeslot)
        self.assertIsNotNone(cls)
        student = self.students[1]

        RegistrationType.objects.get_or_create(name='Priority/1', category='student')
        StudentRegistration.objects.filter(
            user=student,
            relationship__name='Priority/1',
            section__parent_class__parent_program=self.program,
        ).delete()

        # Force unapproved (same condition as handler: status must be > 0)
        ClassSubject.objects.filter(id=cls.id).update(status=ClassStatus.UNREVIEWED)
        ClassSection.objects.filter(id=sec.id).update(status=ClassStatus.UNREVIEWED)
        cls.refresh_from_db()
        sec.refresh_from_db()

        self._ensure_student_profile(student)
        self.assertTrue(
            self.client.login(username=student.username, password='password'),
        )
        payload = {str(timeslot.id): {'1': str(cls.id)}}

        with self.assertLogs(self.LOGGER_NAME, level='WARNING') as log_ctx:
            response = self.client.post(
                '/learn/%s/save_priorities' % self.program.getUrlBase(),
                {'json_data': json.dumps(payload)},
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            any('was not approved' in entry for entry in log_ctx.output),
            'Expected warning log for unapproved class',
        )
        self.assertFalse(
            StudentRegistration.valid_objects().filter(
                user=student,
                relationship__name='Priority/1',
                section__parent_class=cls,
            ).exists(),
            'Must not create Priority/1 registration for unapproved class',
        )
