"""
Behavioral tests for student registration invariants.

Conflict detection, capacity enforcement, and grade filtering are critical
invariants that must hold but had no dedicated regression tests.

Refs: #3780
"""

from esp.program.models import StudentRegistration
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser


class EnrollmentConflictTest(ProgramFrameworkTest):
    """Tests that students cannot enroll in overlapping classes."""

    def setUp(self):
        super().setUp()
        self.add_user_profiles()
        self.schedule_randomly()
        self.student = self.students[0]

    def test_student_can_register_for_class(self):
        """Student can successfully register for a class."""
        section = self.program.sections().filter(
            meeting_times__isnull=False
        ).first()
        self.assertIsNotNone(section, 'Test requires at least one scheduled section')
        
        result = section.preregister_student(self.student)
        self.assertTrue(result, 'preregister_student() should return True for successful registration')
        self.assertTrue(
            StudentRegistration.valid_objects().filter(
                user=self.student,
                section=section,
                relationship__name='Enrolled'
            ).exists(),
            'Student should have valid Enrolled registration'
        )

    def test_conflict_prevents_enrollment_at_same_timeslot(self):
        """Conflict detected when student tries to enroll in overlapping classes."""
        timeslots = list(self.program.getTimeSlots())
        self.assertGreater(len(timeslots), 0, 'Test setup should create timeslots')

        first_timeslot = timeslots[0]

        # Get any two sections - we'll set their times manually
        sections = list(self.program.sections()[:2])
        self.assertGreaterEqual(len(sections), 2, 'Test requires at least 2 sections')
        sec_a, sec_b = sections[0], sections[1]

        # Ensure both sections are at the same timeslot
        sec_a.meeting_times.set([first_timeslot])
        sec_b.meeting_times.set([first_timeslot])

        # First enrollment should succeed
        result_a = sec_a.preregister_student(self.student)
        self.assertTrue(result_a, 'First registration should succeed')

        # Conflict detection must block second enrollment
        error = sec_b.cannotAdd(self.student, checkFull=True, autocorrect_constraints=False)
        self.assertTrue(error, 'cannotAdd() should return an error for conflicting timeslot')
        self.assertIn('conflicts', error.lower(), 'Error message should mention schedule conflicts')


class CapacityEnforcementTest(ProgramFrameworkTest):
    """Tests that section capacity limits are enforced."""

    def setUp(self):
        super().setUp()
        self.add_user_profiles()
        self.schedule_randomly()

    def test_section_under_capacity_accepts_registration(self):
        """Section with available capacity accepts new registration."""
        section = self.program.sections().filter(
            meeting_times__isnull=False
        ).first()
        self.assertIsNotNone(section, 'Test requires at least one scheduled section')

        section.max_class_capacity = 10
        section.save()

        student = self.students[0]
        result = section.preregister_student(student)

        self.assertTrue(result, 'Registration should succeed when section has capacity')
        self.assertTrue(
            StudentRegistration.valid_objects().filter(
                user=student,
                section=section,
                relationship__name='Enrolled'
            ).exists(),
            'Student should be enrolled when capacity available'
        )

    def test_full_section_rejects_new_registration(self):
        """Section at capacity rejects new registration."""
        section = self.program.sections().filter(
            meeting_times__isnull=False
        ).first()
        self.assertIsNotNone(section, 'Test requires at least one scheduled section')

        section.max_class_capacity = 2
        section.save()

        result1 = section.preregister_student(self.students[0])
        self.assertTrue(result1, 'First registration should succeed')

        result2 = section.preregister_student(self.students[1])
        self.assertTrue(result2, 'Second registration should succeed')

        result3 = section.preregister_student(self.students[2])

        self.assertFalse(result3, 'Registration should fail when section is full')
        self.assertFalse(
            StudentRegistration.valid_objects().filter(
                user=self.students[2],
                section=section,
                relationship__name='Enrolled'
            ).exists(),
            'Student should not be enrolled in full section'
        )


class GradeFilterTest(ProgramFrameworkTest):
    """Tests that grade range restrictions are enforced."""

    def setUp(self):
        super().setUp()
        self.add_user_profiles()
        self.schedule_randomly()

    def test_student_in_grade_range_can_enroll(self):
        """Student within grade range can enroll in class."""
        section = self.program.sections().filter(
            meeting_times__isnull=False
        ).first()
        self.assertIsNotNone(section, 'Test requires at least one scheduled section')

        section.parent_class.grade_min = 7
        section.parent_class.grade_max = 12
        section.parent_class.save()

        student = self.students[0]
        schoolyear = ESPUser.program_schoolyear(self.program)
        profile = student.getLastProfile()
        self.assertIsNotNone(profile, 'Student must have a profile')
        self.assertIsNotNone(profile.student_info, 'Student must have student_info')
        
        profile.student_info.graduation_year = schoolyear + 5
        profile.student_info.save()

        error = section.parent_class.cannotAdd(student, checkFull=True)
        self.assertFalse(
            error,
            'ClassSubject.cannotAdd() should allow a student in the grade range'
        )

        result = section.preregister_student(student)
        self.assertTrue(
            result,
            'Student within grade range should be able to register'
        )

    def test_student_outside_grade_range_is_blocked(self):
        """Student outside grade range is blocked from enrolling."""
        section = self.program.sections().filter(
            meeting_times__isnull=False
        ).first()
        self.assertIsNotNone(section, 'Test requires at least one scheduled section')

        section.parent_class.grade_min = 11
        section.parent_class.grade_max = 12
        section.parent_class.save()

        student = self.students[0]
        schoolyear = ESPUser.program_schoolyear(self.program)
        profile = student.getLastProfile()
        self.assertIsNotNone(profile, 'Student must have a profile')
        self.assertIsNotNone(profile.student_info, 'Student must have student_info')
        
        # Grade 6 student: graduates in 6 years (12 - 6 = grade 6)
        profile.student_info.graduation_year = schoolyear + 6
        profile.student_info.save()

        student_grade = student.getGrade(self.program)
        section_grade_min = section.parent_class.grade_min
        section_grade_max = section.parent_class.grade_max

        self.assertFalse(
            section_grade_min <= student_grade <= section_grade_max,
            f'Student grade {student_grade} should be outside range [{section_grade_min}, {section_grade_max}]'
        )

        error = section.parent_class.cannotAdd(student, checkFull=True)
        self.assertTrue(
            error,
            'Student outside grade range should be blocked by ClassSubject.cannotAdd()'
        )
        self.assertIn('requested grade range', error.lower(), 'Error should mention requested grade range')
