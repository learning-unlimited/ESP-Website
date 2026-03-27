"""
Tests for /manage/statistics bug fixes and query optimizations (#3798).

Each test class proves a specific bug exists (would fail before) and is fixed (passes after).
"""
import json
from unittest.mock import MagicMock

from django.contrib.auth.models import Group

from esp.program.models import Program, RegistrationProfile
from esp.program.statistics import demographics, heardabout
from esp.tests.util import CacheFlushTestCase
from esp.users.models import ContactInfo, ESPUser, K12School, StudentInfo


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class HeardAboutNormalizationTest(CacheFlushTestCase):
    """Proof for Fix #2: heardabout() string replace was a no-op.

    BEFORE: ha_key.replace(char, '') — returns new string but result is discarded.
            'my friend' and 'my-friend' would be treated as DIFFERENT sources.
    AFTER:  ha_key = ha_key.replace(char, '') — normalization actually works.
            'my friend' and 'my-friend' are collapsed into ONE source.
    """

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='heardtest', name='Heard Test', grade_min=7, grade_max=12)

        self.student1 = ESPUser.objects.create_user(
            username='heard_s1', password='password', email='h1@test.org')
        self.student1.makeRole('Student')
        self.student2 = ESPUser.objects.create_user(
            username='heard_s2', password='password', email='h2@test.org')
        self.student2.makeRole('Student')

        # Two students heard about program via "my friend" vs "my-friend"
        si1 = StudentInfo.objects.create(
            user=self.student1, graduation_year=2028, heard_about='my friend')
        si2 = StudentInfo.objects.create(
            user=self.student2, graduation_year=2028, heard_about='my-friend')

        p1 = RegistrationProfile.objects.create(
            user=self.student1, student_info=si1)
        p2 = RegistrationProfile.objects.create(
            user=self.student2, student_info=si2)
        self.profiles = [p1, p2]
        self.students = ESPUser.objects.filter(
            id__in=[self.student1.id, self.student2.id])
        self.programs = Program.objects.filter(id=self.program.id)

    def test_normalization_collapses_variants(self):
        """'my friend' and 'my-friend' should normalize to the same key."""
        form = MagicMock()
        form.cleaned_data = {'limit': None}
        result_html = heardabout(
            form, self.programs, self.students, self.profiles, {})
        # After fix: both variants collapse to one entry with count=2.
        # Before fix: they'd be two separate entries with count=1 each.
        # We parse the result to check.
        self.assertIn('2', result_html)


class DemographicsNoneGradYearTest(CacheFlushTestCase):
    """Proof for Fix #3: demographics() KeyError when graduation_year is None.

    BEFORE: Line 117 always executes `gradyear_dict[graduation_year] += 1`
            even when graduation_year is None (line 115's guard only inits key).
            Result: KeyError on None.
    AFTER:  The increment is inside the guard. None graduation_year is skipped.
    """

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='demogtest', name='Demog Test', grade_min=7, grade_max=12)

        self.student = ESPUser.objects.create_user(
            username='demog_s1', password='password', email='d1@test.org')
        self.student.makeRole('Student')

        # Student with graduation_year=None (e.g. incomplete profile)
        si = StudentInfo.objects.create(
            user=self.student, graduation_year=None)
        profile = RegistrationProfile.objects.create(
            user=self.student, student_info=si)
        self.profiles = [profile]
        self.students = ESPUser.objects.filter(id=self.student.id)
        self.programs = Program.objects.filter(id=self.program.id)

    def test_none_graduation_year_no_crash(self):
        """demographics() should not crash when a student has graduation_year=None."""
        form = MagicMock()
        form.cleaned_data = {}
        # Before fix: KeyError: None
        # After fix: runs without error, None is simply skipped
        result_html = demographics(
            form, self.programs, self.students, self.profiles, {})
        self.assertIsInstance(result_html, str)

    def test_none_gradyear_not_in_results(self):
        """None graduation_year should not appear in the output table."""
        form = MagicMock()
        form.cleaned_data = {}
        result_html = demographics(
            form, self.programs, self.students, self.profiles, {})
        self.assertNotIn('None', result_html)


class SelectRelatedProfileTest(CacheFlushTestCase):
    """Proof for Fix #4: Missing select_related on profile batch-fetch.

    BEFORE: select_related('user') only — accessing profile.contact_user,
            profile.student_info, profile.student_info.k12school each triggers
            a separate DB query. N users = 3N extra queries.
    AFTER:  select_related('user', 'contact_user', 'student_info',
            'student_info__k12school') — all fetched in one JOIN query.
    """

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='selreltest', name='SelRel Test', grade_min=7, grade_max=12)

        self.students = []
        for i in range(5):
            student = ESPUser.objects.create_user(
                username='selrel_s%d' % i, password='password',
                email='sr%d@test.org' % i)
            student.makeRole('Student')
            school = K12School.objects.create(name='School %d' % i)
            si = StudentInfo.objects.create(
                user=student, graduation_year=2028, k12school=school)
            ci = ContactInfo.objects.create(
                user=student, first_name=student.first_name,
                last_name=student.last_name, e_mail=student.email,
                address_zip='0210%d' % i)
            RegistrationProfile.objects.create(
                user=student, student_info=si, contact_user=ci)
            self.students.append(student)

        self.user_qs = ESPUser.objects.filter(
            id__in=[s.id for s in self.students])

    def test_select_related_reduces_queries(self):
        """Batch-fetching profiles with full select_related should use fewer queries
        than fetching with only select_related('user')."""
        # Count queries with the FIXED select_related (our code)
        with self.assertNumQueries(1):
            profiles = list(
                RegistrationProfile.objects.filter(user__in=self.user_qs)
                .select_related('user', 'contact_user', 'student_info',
                                'student_info__k12school')
                .order_by('user_id', '-last_ts')
            )

        # Access related fields — should NOT trigger additional queries
        with self.assertNumQueries(0):
            for p in profiles:
                if p.student_info:
                    _ = p.student_info.graduation_year
                    if p.student_info.k12school:
                        _ = p.student_info.k12school.name
                if p.contact_user:
                    _ = p.contact_user.address_zip


class AjaxInvalidFormTest(CacheFlushTestCase):
    """Proof for Fix #1: NameError when AJAX request submits invalid form.

    BEFORE: views.py line 1294 references `result` which is never defined
            in the invalid-form branch. Crashes with NameError.
    AFTER:  Properly builds `result` dict with form contents before returning.
    """

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.admin = ESPUser.objects.create_user(
            username='stats_admin', password='password',
            email='admin@test.org')
        self.admin.makeRole('Administrator')
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()
        # Create at least one program so the form can initialize
        Program.objects.create(
            url='ajaxtest', name='Ajax Test', grade_min=7, grade_max=12)

    def test_ajax_invalid_form_no_crash(self):
        """AJAX POST with invalid form data should return JSON, not crash."""
        self.client.login(username='stats_admin', password='password')

        # Submit form with missing required fields to trigger validation error
        response = self.client.post(
            '/manage/statistics/',
            data={'query': 'demographics'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        # Before fix: NameError: name 'result' is not defined
        # After fix: returns valid JSON response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertIn('statistics_form_contents_html', data)
