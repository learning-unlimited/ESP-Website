from esp.program.tests import ProgramFrameworkTest
from esp.users.views import make_user_admin
from esp.users.models import ESPUser
from esp.tagdict.models import Tag
from esp.program.models import RegistrationType


class RegistrationTypeManagementTest(ProgramFrameworkTest):
    def testTag(self):
        # Create an admin account
        adminUser, created = ESPUser.objects.get_or_create(username='admin')
        adminUser.set_password('password')
        make_user_admin(adminUser)
        # Login as admin
        self.client.login(username='admin', password='password')
        
        # Create the registration types
        testRT = "TestType"
        RegistrationType.objects.get_or_create(name=testRT)
        
        # Try to set the values
        self.client.post("/manage/"+self.program.url()+"/registrationtype_management/", { 'display_names': ["Enrolled", testRT] })

        # Check that the tag was created
        self.failUnless(Tag.objects.filter(key='display_registration_names')[0].value == '["Enrolled", "'+testRT+'"]')

        
