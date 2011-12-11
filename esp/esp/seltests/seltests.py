from django_selenium.testcases import SeleniumTestCase
from esp.seltests import try_login, logout

from esp.users.models import ESPUser

class CsrfTestCase(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)
        user, created = ESPUser.objects.get_or_create(username='student', first_name='Student', last_name='Student')
        user.set_password('student')
        user.save()

    def test_csrf_delete(self):
        self.open_url("/") # Load index

        try_login(self, "student", "student")
        self.failUnless(self.is_text_present('Student Student'))
        logout(self)

        self.delete_cookie("csrftoken")

        try_login(self, "student", "student")
        self.failUnless(self.is_text_present('Please log in to access program registration'))
        logout(self)

        try_login(self, "student", "student")
        self.failUnless(self.is_text_present('Student Student'))
        logout(self)

        self.close()
