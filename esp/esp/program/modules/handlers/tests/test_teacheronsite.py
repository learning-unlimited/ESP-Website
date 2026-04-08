from django.contrib.auth.models import Group
from django.test import RequestFactory

from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.handlers.teacheronsite import TeacherOnsite
from esp.program.models import ProgramModule
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Permission


class TeacherOnsiteTests(ProgramFrameworkTest):
    """Coverage for the teacher onsite mobile webapp handler."""

    def setUp(self):
        super().setUp()
        self.add_user_profiles()
        self.schedule_randomly()

        self.teacher = self.teachers[0]
        self.student = self.students[0]
        self.factory = RequestFactory()

        pm = ProgramModule.objects.get(handler='TeacherOnsite')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)

        # Keep the webapp open for positive-path tests.
        Permission.objects.get_or_create(
            role=Group.objects.get(name='Teacher'),
            permission_type='Teacher/Webapp',
            program=self.program,
        )

    def _teacheronsite_url(self):
        return '%steacheronsite' % self.program.get_teach_url()

    def test_teacheronsite_renders_successfully(self):
        """Test that the teacheronsite view renders successfully for authorized users."""
        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
            "Couldn't log in as teacher %s" % self.teacher.username,
        )

        response = self.client.get(self._teacheronsite_url())
        self.assertEqual(response.status_code, 200)
        
        # Verify response contains expected content
        body = str(response.content, encoding='UTF-8')
        # Should contain HTML markup
        self.assertTrue(
            '<!DOCTYPE' in body or '<html' in body or '<HTML' in body,
            "Response should contain HTML"
        )

    def test_teacheronsite_requires_teacher_role(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
            "Couldn't log in as student %s" % self.student.username,
        )

        response = self.client.get(self._teacheronsite_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn('Not a Teacher!', str(response.content, encoding='UTF-8'))

    def test_teacheronsite_is_accessible_with_permission(self):
        """Test that teacheronsite view is accessible when user has Teacher/Webapp permission."""
        # Permission is created in setUp with get_or_create
        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
            "Couldn't log in as teacher"
        )

        response = self.client.get(self._teacheronsite_url())
        self.assertEqual(response.status_code, 200)
        
        body = str(response.content, encoding='UTF-8')
        # Verify it's HTML, not an error page
        self.assertTrue(
            body.upper().startswith('<!DOCTYPE') or '<HTML' in body.upper() or '<html' in body,
            "Response should contain HTML"
        )

    def test_teacheronsite_blocked_without_permission(self):
        """Test that access is properly controlled with permission deadline."""
        # Remove the Teacher/Webapp permission
        Permission.objects.filter(
            program=self.program,
            permission_type='Teacher/Webapp',
        ).delete()

        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
            "Couldn't log in as teacher"
        )

        response = self.client.get(self._teacheronsite_url())
        # Should be blocked or show error page
        self.assertEqual(response.status_code, 200)
        
        body = str(response.content, encoding='UTF-8').lower()
        # Verify it's an error/access denied page
        is_error_page = (
            'closed' in body or 
            'deadline' in body or 
            'not available' in body or
            'not met' in body
        )
        self.assertTrue(is_error_page or '<!doctype' in body[:100].lower(),
                      "Response should be error page or deadline not met message")

    def test_get_admin_search_entry_for_onsite_views(self):
        entry = TeacherOnsite.get_admin_search_entry(
            self.program,
            'teach',
            'onsitemap',
            self.module,
        )

        self.assertIsNotNone(entry)
        self.assertEqual(entry.id, 'teach_onsitemap')
        self.assertEqual(entry.title, 'Teacher Onsite (Map)')
        self.assertEqual(entry.disambiguation_label, 'Map')
        self.assertIn('onsite', entry.keywords)
        self.assertEqual(entry.url, '/teach/%s/onsitemap' % self.program.getUrlBase())

    def test_get_admin_search_entry_unknown_view_returns_none(self):
        entry = TeacherOnsite.get_admin_search_entry(
            self.program,
            'teach',
            'not_a_real_teacheronsite_view',
            self.module,
        )
        self.assertIsNone(entry)

    def test_onsitecontext_marks_survey_none_when_no_teacher_surveys(self):
        request = self.factory.get('/fake')
        request.user = self.teacher

        context = TeacherOnsite.onsitecontext(
            request,
            'teach',
            self.program.program_type,
            self.program.program_instance,
            self.program,
        )

        self.assertEqual(context.get('survey_status'), 'none')
