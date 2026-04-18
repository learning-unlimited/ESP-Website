"""
Unit tests for esp/web/views/bio.py

Covers:
  - bio_not_found()         — 404 response
  - bio_user()              — inactive, hidden, old_url, defaults, active
  - bio()                   — username lookup, old_url, not found
  - bio_edit_user_program() — permission checks, GET form, POST save

PR 5/6 — esp/web module coverage improvement
"""

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

from esp.tests.util import CacheFlushTestCase
from esp.users.models import ESPUser
from esp.program.models import TeacherBio
from esp.web.views.bio import bio_not_found, bio_user, bio, bio_edit_user_program


def _make_teacher(username, password='testpass'):
    user = ESPUser.objects.create_user(
        username=username,
        password=password,
        email='%s@test.com' % username,
        first_name='Test',
        last_name='Teacher',
    )
    from django.contrib.auth.models import Group
    teacher_group, _ = Group.objects.get_or_create(name='Teacher')
    user.groups.add(teacher_group)
    return user


def _make_student(username, password='testpass'):
    user = ESPUser.objects.create_user(
        username=username,
        password=password,
        email='%s@test.com' % username,
        first_name='Test',
        last_name='Student',
    )
    from django.contrib.auth.models import Group
    student_group, _ = Group.objects.get_or_create(name='Student')
    user.groups.add(student_group)
    return user


def _make_admin(username, password='testpass'):
    user = ESPUser.objects.create_superuser(
        username=username,
        password=password,
        email='%s@test.com' % username,
    )
    from django.contrib.auth.models import Group
    admin_group, _ = Group.objects.get_or_create(name='Administrator')
    user.groups.add(admin_group)
    return user


# ---------------------------------------------------------------------------
# bio_not_found()
# ---------------------------------------------------------------------------

class BioNotFoundTest(CacheFlushTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_404_status(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio_not_found(request)
        self.assertEqual(response.status_code, 404)

    def test_with_user_still_404(self):
        teacher = _make_teacher('bnf_teacher')
        request = self.factory.get('/')
        request.user = teacher
        response = bio_not_found(request, user=teacher)
        self.assertEqual(response.status_code, 404)

    def test_with_edit_url_still_404(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio_not_found(request, edit_url='/teach/bio/edit/')
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# bio_user()
# ---------------------------------------------------------------------------

class BioUserTest(CacheFlushTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_none_user_returns_404(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio_user(request, None)
        self.assertEqual(response.status_code, 404)

    def test_inactive_user_returns_404(self):
        teacher = _make_teacher('inactive_teacher')
        teacher.is_active = False
        teacher.save()
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio_user(request, teacher)
        self.assertEqual(response.status_code, 404)

    def test_non_teacher_returns_404(self):
        student = _make_student('bio_student')
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio_user(request, student)
        self.assertEqual(response.status_code, 404)

    def test_hidden_bio_returns_404(self):
        teacher = _make_teacher('hidden_teacher')
        bio_obj = TeacherBio.getLastBio(teacher)
        bio_obj.hidden = True
        bio_obj.save()
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio_user(request, teacher)
        self.assertEqual(response.status_code, 404)

    def test_old_url_returns_redirect(self):
        teacher = _make_teacher('oldurl_teacher')
        teacherbio = TeacherBio.getLastBio(teacher)
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio_user(request, teacher, old_url=True)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], teacherbio.url())

    def test_active_teacher_returns_200(self):
        teacher = _make_teacher('active_teacher')
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio_user(request, teacher, old_url=False)
        self.assertEqual(response.status_code, 200)

    def test_missing_picture_filled_with_default(self):
        teacher = _make_teacher('nopic_teacher')
        bio_obj = TeacherBio.getLastBio(teacher)
        bio_obj.picture = None
        bio_obj.save()
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio_user(request, teacher, old_url=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['bio'].picture, 'images/not-available.jpg')

    def test_empty_slugbio_filled_with_default(self):
        teacher = _make_teacher('noslug_teacher')
        bio_obj = TeacherBio.getLastBio(teacher)
        bio_obj.slugbio = '   '
        bio_obj.save()
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio_user(request, teacher, old_url=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['bio'].slugbio, 'ESP Teacher')

    def test_empty_bio_filled_with_default(self):
        teacher = _make_teacher('nobio_teacher')
        bio_obj = TeacherBio.getLastBio(teacher)
        bio_obj.bio = ''
        bio_obj.save()
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio_user(request, teacher, old_url=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['bio'].bio, 'Not Available.')


# ---------------------------------------------------------------------------
# bio() view
# ---------------------------------------------------------------------------

class BioViewTest(CacheFlushTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_valid_username_returns_200(self):
        teacher = _make_teacher('bio_view_teacher')
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio(request, tl='teach', username=teacher.username)
        self.assertEqual(response.status_code, 200)

    def test_old_tl_returns_redirect(self):
        teacher = _make_teacher('redirect_teacher')
        request = self.factory.get('/')
        request.user = AnonymousUser()
        # tl != 'teach' → old_url=True → 301
        response = bio(request, tl='learn', username=teacher.username)
        self.assertEqual(response.status_code, 301)

    def test_teach_tl_not_old_url(self):
        teacher = _make_teacher('teach_tl_teacher')
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = bio(request, tl='teach', username=teacher.username)
        # should NOT be a redirect — it's the current URL pattern
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# bio_edit_user_program()
# ---------------------------------------------------------------------------

class BioEditUserProgramTest(CacheFlushTestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.teacher = _make_teacher('edit_teacher')
        self.admin = _make_admin('edit_admin')

    def test_none_user_returns_404(self):
        request = self.factory.get('/')
        request.user = self.teacher
        response = bio_edit_user_program(request, None, None)
        self.assertEqual(response.status_code, 404)

    def test_non_teacher_returns_404(self):
        student = _make_student('edit_student')
        request = self.factory.get('/')
        request.user = self.teacher
        response = bio_edit_user_program(request, student, None)
        self.assertEqual(response.status_code, 404)

    def test_different_user_non_admin_returns_404(self):
        other_teacher = _make_teacher('other_edit_teacher')
        request = self.factory.get('/')
        request.user = other_teacher
        response = bio_edit_user_program(request, self.teacher, None)
        self.assertEqual(response.status_code, 404)

    def test_owner_get_returns_200(self):
        request = self.factory.get('/')
        request.user = self.teacher
        response = bio_edit_user_program(request, self.teacher, None)
        self.assertEqual(response.status_code, 200)

    def test_admin_can_edit_other_teacher(self):
        request = self.factory.get('/')
        request.user = self.admin
        response = bio_edit_user_program(request, self.teacher, None)
        self.assertEqual(response.status_code, 200)

    def test_old_url_returns_301(self):
        lastbio = TeacherBio.getLastBio(self.teacher)
        request = self.factory.get('/')
        request.user = self.teacher
        response = bio_edit_user_program(
            request, self.teacher, None, old_url=True
        )
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], lastbio.edit_url())

    def test_valid_post_saves_and_redirects(self):
        # Omit 'hidden' to simulate an unchecked checkbox (BooleanField treats
        # the string 'False' as truthy, so we must omit it for hidden=False).
        request = self.factory.post('/', {
            'bio_submitted': '1',
            'slugbio': 'Math lover',
            'bio': 'I teach math.',
        })
        request.user = self.teacher
        response = bio_edit_user_program(request, self.teacher, None)
        # successful save → redirect
        self.assertEqual(response.status_code, 302)
        bio_obj = TeacherBio.getLastBio(self.teacher)
        self.assertEqual(bio_obj.slugbio, 'Math lover')
        self.assertEqual(bio_obj.bio, 'I teach math.')
        self.assertFalse(bio_obj.hidden)

    def test_post_without_bio_submitted_key_renders_form(self):
        request = self.factory.post('/', {
            'slugbio': 'Ignored',
        })
        request.user = self.teacher
        response = bio_edit_user_program(request, self.teacher, None)
        # no bio_submitted key → treated as GET → renders form
        self.assertEqual(response.status_code, 200)

    def test_post_slugbio_too_long_rerenders_form(self):
        # Omit 'hidden' to avoid BooleanField coercing the string 'False' as truthy.
        request = self.factory.post('/', {
            'bio_submitted': '1',
            'slugbio': 'x' * 51,   # max_length=50
            'bio': 'Some bio.',
        })
        request.user = self.teacher
        response = bio_edit_user_program(request, self.teacher, None)
        # invalid form → re-render, not redirect
        self.assertEqual(response.status_code, 200)
