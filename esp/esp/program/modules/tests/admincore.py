from esp.program.tests import ProgramFrameworkTest
from esp.users.views import make_user_admin
from esp.users.models import ESPUser
from esp.tagdict.models import Tag
from esp.program.models import RegistrationType, StudentRegistration, RegistrationProfile, ProgramModule


class RegistrationTypeManagementTest(ProgramFrameworkTest):
    def setUp(self):
        modules = []
        modules.append(ProgramModule.objects.get(handler='TeacherClassRegModule').id)
        modules.append(ProgramModule.objects.get(handler='StudentClassRegModule').id)
        modules.append(ProgramModule.objects.get(handler='StudentRegCore').id)
        modules.append(ProgramModule.objects.get(handler='AdminCore').id)
        
        super(RegistrationTypeManagementTest, self).setUp(modules=modules)
        self.schedule_randomly()

        # Create registration types
        self.testRT = "TestType"
        RegistrationType.objects.get_or_create(name=self.testRT)
        RegistrationType.objects.get_or_create(name='Enrolled')


        # Create an admin account
        self.adminUser, created = ESPUser.objects.get_or_create(username='admin')
        self.adminUser.set_password('password')
        make_user_admin(self.adminUser)

        
    def testAdminInterface(self):
        # Login as admin
        self.client.login(username='admin', password='password')
        
        # Try to set the values
        r = self.client.post("/manage/"+self.program.url+"/registrationtype_management/", { 'display_names': ["Enrolled", self.testRT] })

        # Check that the tag was created
        self.failUnless(len(Tag.objects.filter(key='display_registration_names')) > 0)
        self.failUnless(Tag.objects.filter(key='display_registration_names')[0].value == '["Enrolled", "'+self.testRT+'"]')

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
        self.failUnless(not self.testRT in r.content)

        # Then set the tag
        Tag.objects.get_or_create(key='display_registration_names', value='["Enrolled", "'+self.testRT+'"]')
        # Check the displayed types again
        r = self.client.get("/learn/"+self.program.url+"/studentreg")
        self.failUnless(self.testRT in r.content)
