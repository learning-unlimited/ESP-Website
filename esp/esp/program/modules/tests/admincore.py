from __future__ import absolute_import
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser
from esp.tagdict.models import Tag
from esp.program.models import RegistrationType, StudentRegistration, RegistrationProfile, ProgramModule
from esp.program.modules.base import ProgramModuleObj


class RegistrationTypeManagementTest(ProgramFrameworkTest):
    def setUp(self):
        modules = []
        modules.append(ProgramModule.objects.get(handler='TeacherClassRegModule'))
        modules.append(ProgramModule.objects.get(handler='StudentClassRegModule'))
        modules.append(ProgramModule.objects.get(handler='StudentRegCore'))
        modules.append(ProgramModule.objects.get(handler='AdminCore'))

        super(RegistrationTypeManagementTest, self).setUp(modules=modules)
        self.schedule_randomly()

        # Create registration types
        self.testRT = "TestType"
        RegistrationType.objects.get_or_create(name=self.testRT)
        RegistrationType.objects.get_or_create(name='Enrolled')


        # Create an admin account
        self.adminUser, created = ESPUser.objects.get_or_create(username='admin')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()

        scrmi = self.program.studentclassregmoduleinfo
        scrmi.force_show_required_modules = False
        scrmi.save()


    def testAdminInterface(self):
        # Login as admin
        self.client.login(username='admin', password='password')

        # Try to set the values
        r = self.client.post("/manage/"+self.program.url+"/registrationtype_management/", { 'display_names': ["Enrolled", self.testRT] })

        # Check that the tag was created
        self.assertTrue(len(Tag.objects.filter(key='display_registration_names')) > 0)
        self.assertTrue(Tag.objects.filter(key='display_registration_names')[0].value == '["Enrolled", "'+self.testRT+'"]')

    def testCorrectness(self):
        # Get a student and give them relationship of Enrolled and another with a class
        student = self.students[0]
        cls = self.teachers[0].getTaughtSectionsFromProgram(self.program)[0]
        StudentRegistration.objects.get_or_create(user=student, section=cls, relationship=RegistrationType.objects.get(name='Enrolled'))
        StudentRegistration.objects.get_or_create(user=student, section=cls, relationship=RegistrationType.objects.get(name=self.testRT))
        # Login with the student account
        student.set_password('password')
        self.client.login(username=student.username, password='password')

        # Initially, delete the tag
        Tag.objects.filter(key='display_registration_names').delete()
        # Check the displayed types
        r = self.client.get("/learn/"+self.program.url+"/studentreg")
        self.assertNotContains(r, self.testRT, status_code=200)

        # Then set the tag
        Tag.objects.get_or_create(key='display_registration_names', value='["Enrolled", "'+self.testRT+'"]')
        # Check the displayed types again
        r = self.client.get("/learn/"+self.program.url+"/studentreg")
        self.assertContains(r, self.testRT, status_code=200)


class ModuleManagementLinkTitleTest(ProgramFrameworkTest):
    """Tests for the per-program link_title override on the Module Management page."""

    def setUp(self):
        modules = []
        modules.append(ProgramModule.objects.get(handler='StudentClassRegModule'))
        modules.append(ProgramModule.objects.get(handler='TeacherClassRegModule'))
        modules.append(ProgramModule.objects.get(handler='AdminCore'))

        super(ModuleManagementLinkTitleTest, self).setUp(modules=modules)

        # Create a dedicated admin account for these tests
        self.adminUser, created = ESPUser.objects.get_or_create(username='admin_modmgmt')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()

    def _modules_url(self):
        return '/manage/' + self.program.url + '/modules/'

    def test_get_link_title_default_fallback(self):
        """get_link_title() returns the module's default title when link_title is blank."""
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        pmo.link_title = ""
        pmo.save()
        self.assertEqual(pmo.get_link_title(), pmo.module.link_title)

    def test_get_link_title_override(self):
        """get_link_title() returns the per-program override when it is set."""
        pmo = ProgramModuleObj.objects.filter(program=self.program).first()
        pmo.link_title = "My Custom Title"
        pmo.save()
        self.assertEqual(pmo.get_link_title(), "My Custom Title")

    def test_module_management_saves_link_title(self):
        """Submitting the module management form saves link_title for each module."""
        self.client.login(username='admin_modmgmt', password='password')

        learn_mods = [m for m in self.program.getModules(tl='learn') if m.inModulesList()]
        teach_mods = [m for m in self.program.getModules(tl='teach') if m.inModulesList()]

        learn_req_ids    = [str(m.id) for m in learn_mods if m.required]
        learn_not_req_ids = [str(m.id) for m in learn_mods if not m.required]
        teach_req_ids    = [str(m.id) for m in teach_mods if m.required]
        teach_not_req_ids = [str(m.id) for m in teach_mods if not m.required]

        all_ids = learn_req_ids + learn_not_req_ids + teach_req_ids + teach_not_req_ids

        post_data = {
            'learn_req':     ','.join(learn_req_ids),
            'learn_not_req': ','.join(learn_not_req_ids),
            'teach_req':     ','.join(teach_req_ids),
            'teach_not_req': ','.join(teach_not_req_ids),
        }
        for mod_id in all_ids:
            post_data['%s_label' % mod_id]      = ''
            post_data['%s_link_title' % mod_id] = 'Custom Title for %s' % mod_id

        r = self.client.post(self._modules_url(), post_data)
        self.assertIn(r.status_code, [200, 302])

        for mod_id in all_ids:
            pmo = ProgramModuleObj.objects.get(id=int(mod_id))
            self.assertEqual(pmo.link_title, 'Custom Title for %s' % mod_id)

    def test_module_management_resets_link_title(self):
        """POSTing with default_link_title resets all link_title overrides to empty."""
        self.client.login(username='admin_modmgmt', password='password')

        # Give every module a non-empty link_title override
        for pmo in ProgramModuleObj.objects.filter(program=self.program):
            pmo.link_title = "Custom Title"
            pmo.save()

        r = self.client.post(self._modules_url(), {'default_link_title': 'on'})
        self.assertIn(r.status_code, [200, 302])

        for pmo in ProgramModuleObj.objects.filter(program=self.program):
            self.assertEqual(pmo.link_title, "")

    def test_module_management_link_title_reset_independent(self):
        """default_link_title alone triggers the reset without requiring other reset flags."""
        self.client.login(username='admin_modmgmt', password='password')

        for pmo in ProgramModuleObj.objects.filter(program=self.program):
            pmo.link_title = "Should be cleared"
            pmo.seq = 999
            pmo.save()

        # Only send default_link_title — seq and required should NOT change
        r = self.client.post(self._modules_url(), {'default_link_title': 'on'})
        self.assertIn(r.status_code, [200, 302])

        for pmo in ProgramModuleObj.objects.filter(program=self.program):
            self.assertEqual(pmo.link_title, "")
            # seq should be unchanged (not reset) because default_seq was not sent
            self.assertEqual(pmo.seq, 999)
