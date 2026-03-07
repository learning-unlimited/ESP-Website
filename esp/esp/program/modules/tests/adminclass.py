from esp.program.tests import ProgramFrameworkTest
from esp.program.class_status import ClassStatus
from esp.program.models import ClassSubject
from esp.users.models import ESPUser
from django.core import mail

class CancelClassTest(ProgramFrameworkTest):
    def setUp(self):
        # Set up the program framework and randomly schedule classes
        super().setUp()
        self.schedule_randomly()

        # Find a class to be cancelled
        self.cls = self.teachers[0].getTaughtClasses()[0]
        # Put a student in it
        self.student = self.students[0]
        self.student.email = "testing@localhost"
        self.student.save()
        self.cls.sections.all()[0].preregister_student(self.student, True, True)

        # Create an admin account
        self.adminUser, created = ESPUser.objects.get_or_create(username='admin')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()
        self.adminUser.save()

    def testCancelClass(self):
        # Login with the admin account
        self.client.login(username='admin', password='password')

        # Cancel the class
        cancelMsg = 'Testing cancel class'
        self.client.post("/manage/"+self.program.url+"/manageclass/"+str(self.cls.id)+"?action=cancel_cls", { 'acknowledgement': 'on', 'explanation': cancelMsg, 'target': self.cls.id })

        # Update the class
        self.cls = ClassSubject.objects.get(pk=self.cls.id)

        # Check that the class was changed to cancelled
        self.assertEqual(self.cls.status, ClassStatus.CANCELLED)
        # Check that the sections were cancelled
        for sec in self.cls.sections.all():
            self.assertEqual(sec.status, ClassStatus.CANCELLED)

        # Test that an email was sent
        directorEmail = None
        studentEmail = None
        for m in mail.outbox:
            for addr in m.to:
                if self.program.director_email in addr:
                    directorEmail = m
                    break
                if self.student.email in addr:
                    studentEmail = m
                    break

        self.assertTrue(directorEmail is not None and cancelMsg in directorEmail.body)
        self.assertTrue(studentEmail is not None and cancelMsg in studentEmail.body)

        # Check that classes show up in the cancelled classes printable
        r = self.client.get("/manage/"+self.program.url+"/classesbytime?cancelled")
        self.assertContains(r, self.cls.emailcode(), status_code=200)
class EditClassViewTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        self.schedule_randomly()

        # Select a class
        self.cls = self.teachers[0].getTaughtClasses()[0]

        # Create admin user
        self.adminUser, created = ESPUser.objects.get_or_create(username='admin2')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()
        self.adminUser.save()

    def test_editclass_page_loads(self):
        self.client.login(username='admin2', password='password')

        url = "/manage/" + self.program.url + "/editclass/" + str(self.cls.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_editclass_requires_login(self):
        url = "/manage/" + self.program.url + "/editclass/" + str(self.cls.id)
        response = self.client.get(url)

        # Expect redirect to login page
        self.assertEqual(response.status_code, 302)