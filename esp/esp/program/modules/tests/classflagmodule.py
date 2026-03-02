import json

from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ClassFlag, ClassFlagType
from esp.middleware.threadlocalrequest import _threading_local


class ClassFlagModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        # Clear stale thread-local request BEFORE super().setUp()
        # to prevent ClassFlag.save() from using a stale request object.
        if hasattr(_threading_local, 'request'):
            del _threading_local.request

        super(ClassFlagModuleTest, self).setUp(
            num_students=0, num_teachers=1, num_admins=1, *args, **kwargs)

        self.program.getModules()

        self.admin_user = self.admins[0]
        self.subject = self.program.classes()[0]

        self.flag_type = ClassFlagType.objects.create(
            name='Test Flag', color='#ff0000')
        self.program.flag_types.add(self.flag_type)

        # Create flag with EXPLICIT fields to bypass thread-local save()
        self.flag = ClassFlag.objects.create(
            subject=self.subject, flag_type=self.flag_type,
            comment='test comment',
            created_by=self.admin_user, modified_by=self.admin_user,
        )

        self.client.login(username=self.admin_user.username, password='password')
        self.base_url = '/manage/' + self.program.url

    def test_create_flag(self):
        """POST to newflag creates a new ClassFlag."""
        flag_type2 = ClassFlagType.objects.create(
            name='Test Flag 2', color='#00ff00')
        self.program.flag_types.add(flag_type2)

        response = self.client.post(self.base_url + '/newflag/', {
            'subject': self.subject.id,
            'flag_type': flag_type2.id,
            'comment': 'new flag comment',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ClassFlag.objects.filter(
                subject=self.subject, flag_type=flag_type2).exists())

    def test_edit_flag_comment(self):
        """POST to editflag updates the comment and returns JSON."""
        response = self.client.post(
            self.base_url + '/editflag/%d/' % self.flag.id,
            {'comment': 'updated comment'})
        self.assertEqual(response.status_code, 200)
        self.flag.refresh_from_db()
        self.assertEqual(self.flag.comment, 'updated comment')

    def test_editflag_returns_json(self):
        """editflag response has application/json content type with flag_detail key."""
        response = self.client.post(
            self.base_url + '/editflag/%d/' % self.flag.id,
            {'comment': 'json test'})
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        self.assertIn('flag_detail', data)

    def test_resolve_flag(self):
        """POST to resolveflag with action=resolve sets resolved=True with audit trail."""
        response = self.client.post(
            self.base_url + '/resolveflag/%d/' % self.flag.id,
            {'action': 'resolve'})
        self.assertEqual(response.status_code, 200)
        self.flag.refresh_from_db()
        self.assertTrue(self.flag.resolved)
        self.assertEqual(self.flag.resolved_by, self.admin_user)
        self.assertIsNotNone(self.flag.resolved_time)

    def test_unresolve_flag(self):
        """POST to resolveflag with action=unresolve clears resolved status."""
        # First resolve
        self.flag.resolved = True
        self.flag.resolved_by = self.admin_user
        self.flag.save()
        # Then unresolve
        response = self.client.post(
            self.base_url + '/resolveflag/%d/' % self.flag.id,
            {'action': 'unresolve'})
        self.assertEqual(response.status_code, 200)
        self.flag.refresh_from_db()
        self.assertFalse(self.flag.resolved)
        self.assertIsNone(self.flag.resolved_by)
        self.assertIsNone(self.flag.resolved_time)

    def test_resolve_is_idempotent(self):
        """POST action=resolve on already-resolved flag is a no-op (idempotent)."""
        # Resolve first
        self.client.post(
            self.base_url + '/resolveflag/%d/' % self.flag.id,
            {'action': 'resolve'})
        self.flag.refresh_from_db()
        original_time = self.flag.resolved_time
        # Resolve again — should be idempotent
        response = self.client.post(
            self.base_url + '/resolveflag/%d/' % self.flag.id,
            {'action': 'resolve'})
        self.assertEqual(response.status_code, 200)
        self.flag.refresh_from_db()
        self.assertTrue(self.flag.resolved)
        self.assertEqual(self.flag.resolved_time, original_time)

    def test_resolve_returns_updated_html(self):
        """resolveflag returns JSON with flag_name and flag_detail containing resolved indicators."""
        response = self.client.post(
            self.base_url + '/resolveflag/%d/' % self.flag.id,
            {'action': 'resolve'})
        data = json.loads(response.content)
        self.assertIn('flag_name', data)
        self.assertIn('flag_detail', data)
        self.assertIn('Unresolve', data['flag_detail'])
        self.assertIn('(Resolved)', data['flag_name'])

    def test_delete_flag(self):
        """POST to deleteflag removes the flag."""
        flag_id = self.flag.id
        response = self.client.post(
            self.base_url + '/deleteflag/',
            {'id': flag_id})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ClassFlag.objects.filter(id=flag_id).exists())

    def test_cross_program_idor_blocked(self):
        """resolveflag scoped to current program rejects flags from other programs."""
        from esp.program.models import Program
        from esp.program.models.class_ import ClassSubject

        # Create a second program + class directly via Model API
        # (not via ProgramFrameworkTest().setUp() which leaks DB transactions)
        other_prog = Program.objects.create(
            url='OtherProgram/2223_Summer',
            name='OtherProgram Summer 2223',
            grade_min=7, grade_max=12,
        )
        other_subject = ClassSubject.objects.create(
            title='Other class', parent_program=other_prog,
            category=self.subject.category,
            grade_min=7, grade_max=12, class_size_max=30,
        )

        other_flag = ClassFlag.objects.create(
            subject=other_subject, flag_type=self.flag_type,
            comment='other program flag',
            created_by=self.admin_user, modified_by=self.admin_user,
        )

        # Try to resolve other program's flag via THIS program's URL
        response = self.client.post(
            self.base_url + '/resolveflag/%d/' % other_flag.id,
            {'action': 'resolve'})
        self.assertEqual(response.status_code, 400)
        other_flag.refresh_from_db()
        self.assertFalse(other_flag.resolved)

    def test_newflag_cross_program_subject_idor_blocked(self):
        """newflag rejects creating a flag on a subject from another program."""
        from esp.program.models import Program
        from esp.program.models.class_ import ClassSubject

        other_prog = Program.objects.create(
            url='OtherProgram/2224_Summer',
            name='OtherProgram Summer 2224',
            grade_min=7, grade_max=12,
        )
        other_subject = ClassSubject.objects.create(
            title='Other class', parent_program=other_prog,
            category=self.subject.category,
            grade_min=7, grade_max=12, class_size_max=30,
        )

        response = self.client.post(self.base_url + '/newflag/', {
            'subject': other_subject.id,
            'flag_type': self.flag_type.id,
            'comment': 'cross-program attack',
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            ClassFlag.objects.filter(subject=other_subject).exists())

    def test_newflag_cross_program_flagtype_idor_blocked(self):
        """newflag rejects creating a flag with a flag_type not in this program."""
        other_flag_type = ClassFlagType.objects.create(
            name='Alien Flag', color='#000000')
        # NOT added to self.program.flag_types

        response = self.client.post(self.base_url + '/newflag/', {
            'subject': self.subject.id,
            'flag_type': other_flag_type.id,
            'comment': 'alien flag type attack',
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            ClassFlag.objects.filter(flag_type=other_flag_type).exists())

    def test_search_flag_with_resolved_status(self):
        """Search with flag filter + unresolved status excludes resolved flags."""
        # Ensure we have a second class (ProgramFrameworkTest creates 2 per teacher)
        all_classes = list(self.program.classes())
        self.assertGreaterEqual(len(all_classes), 2,
            "Need at least 2 classes to test exclusion")
        subject2 = all_classes[1]

        resolved_flag = ClassFlag.objects.create(
            subject=subject2, flag_type=self.flag_type,
            comment='resolved flag', resolved=True,
            created_by=self.admin_user, modified_by=self.admin_user,
            resolved_by=self.admin_user,
        )

        # Search for unresolved flags of this type
        query = json.dumps({
            'filter': 'flag',
            'negated': False,
            'values': [str(self.flag_type.id), None, None, 'unresolved'],
        })
        response = self.client.get(
            self.base_url + '/classsearch/', {'query': query})
        self.assertEqual(response.status_code, 200)
        # The unresolved flag's subject should be in results
        self.assertContains(response, self.subject.emailcode())
        # The resolved flag's subject must NOT be in results
        self.assertNotContains(response, subject2.emailcode())
