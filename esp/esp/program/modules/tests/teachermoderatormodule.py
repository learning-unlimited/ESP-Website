"""
Unit tests for TeacherModeratorModule (teachermoderatormodule.py).
"""
import json

from esp.program.models import ModeratorRecord
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest


class TeacherModeratorModuleTest(ModuleHandlerTestMixin, ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_students': 1,
            'num_teachers': 3,
            'num_admins': 1,
            'num_timeslots': 3,
        })
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        self.module = self.get_module_obj('TeacherModeratorModule')

    def _url(self):
        return self.get_module_url('teach', 'moderate')

    def _post_moderate(self, **fields):
        cat = self.program.class_categories.first()
        data = {
            'will_moderate': 'on',
            'num_slots': '1',
            'comments': '',
        }
        if cat:
            data['class_categories'] = [str(cat.id)]
        data.update(fields)
        return self.client.post(self._url(), data)

    def test_moderate_form_renders_for_teacher(self):
        self.login_as('teacher')
        response = self.assert_view_ok(self._url())
        self.assertIn('form', response.context)
        self.assertTemplateUsed(response, 'program/modules/teachermoderatormodule/moderate.html')

    def test_student_cannot_access_moderate(self):
        self.login_as('student')
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'errors/program/notateacher.html')

    def test_create_moderator_record(self):
        teacher = self.login_as('teacher')
        response = self._post_moderate(comments='Happy to help')
        # Valid form redirects to teacher core
        self.assertEqual(response.status_code, 302, getattr(response, 'context', None) and response.context.get('form') and response.context['form'].errors)
        self.assertTrue(
            ModeratorRecord.objects.filter(user=teacher, program=self.program).exists()
        )
        rec = ModeratorRecord.objects.get(user=teacher, program=self.program)
        self.assertTrue(rec.will_moderate)
        self.assertEqual(rec.num_slots, 1)
        self.assertEqual(rec.comments, 'Happy to help')

    def test_edit_existing_moderator_record(self):
        teacher = self.teachers[0]
        ModeratorRecord.objects.create(
            user=teacher, program=self.program, will_moderate=False, num_slots=1
        )
        self.login_as('teacher')
        response = self._post_moderate(num_slots='2', comments='Updated')
        self.assertEqual(response.status_code, 302, getattr(response, 'context', None) and response.context.get('form') and response.context['form'].errors)
        rec = ModeratorRecord.objects.get(user=teacher, program=self.program)
        self.assertTrue(rec.will_moderate)
        self.assertEqual(rec.num_slots, 2)
        self.assertEqual(rec.comments, 'Updated')

    def test_is_completed_false_without_record(self):
        teacher = self.teachers[1]
        self.assertFalse(self.module.isCompleted(user=teacher))

    def test_is_completed_true_with_record(self):
        teacher = self.teachers[1]
        ModeratorRecord.objects.create(
            user=teacher, program=self.program, will_moderate=True, num_slots=1
        )
        self.assertTrue(self.module.isCompleted(user=teacher))

    def test_teachers_queryset_will_moderate(self):
        t0, t1 = self.teachers[0], self.teachers[1]
        ModeratorRecord.objects.create(
            user=t0, program=self.program, will_moderate=True, num_slots=1
        )
        ModeratorRecord.objects.create(
            user=t1, program=self.program, will_moderate=False, num_slots=0
        )
        result = self.module.teachers(QObject=False)
        self.assertIn(t0, result['will_moderate'])
        self.assertNotIn(t1, result['will_moderate'])

    def test_teachers_qobject_keys(self):
        result = self.module.teachers(QObject=True)
        self.assertIn('will_moderate', result)
        self.assertIn('assigned_moderator', result)

    def test_moderatorlookup_returns_json(self):
        teacher = self.teachers[0]
        ModeratorRecord.objects.create(
            user=teacher, program=self.program, will_moderate=True, num_slots=1
        )
        self.login_as('admin')
        url = self.get_module_url('teach', 'moderatorlookup')
        response = self.client.get(url, {'name': teacher.last_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'].split(';')[0], 'application/json')
        payload = json.loads(response.content.decode('utf-8'))
        self.assertTrue(any(item.get('id') == teacher.id for item in payload))
