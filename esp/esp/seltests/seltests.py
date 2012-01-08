from django_selenium.testcases import SeleniumTestCase
from esp.seltests import try_ajax_login, try_normal_login, logout

from esp.utils.models import TemplateOverride
from esp.users.models import ESPUser

class CsrfTestCase(SeleniumTestCase):
    def setUp(self):
        super(CsrfTestCase, self).setUp()
        user, created = ESPUser.objects.get_or_create(username='student', first_name='Student', last_name='Student')
        user.set_password('student')
        user.save()
        # Save the last good version of the template override in question
        if len(TemplateOverride.objects.filter(name='index.html')) == 0:
             # There are no existing template overrides
             self.good_version = -1
        else:
             to = TemplateOverride.objects.filter(name='index.html')[0]
             self.good_version = to.next_version() - 1

    def tearDown(self):
        if (self.good_version > 1):
            # Tear down the template override for consistent behavior
            last_good_to = TemplateOverride.objects.filter(name='index.html', version=self.good_version)
            last_good_to.save()
        else:
            # We need to get rid of the template override entirely
            TemplateOverride.objects.filter(name='index.html').delete()

    def setUpNormalLogin(self):
        if(self.good_version == -1):
             to, created = TemplateOverride.objects.get_or_create(name='index.html', version=1)
        else:
             to = TemplateOverride.objects.filter(name='index.html')[0]
        to.content = """
             {% extends "elements/html" %}

             {% block body %}
             {% include "users/loginbox.html" %}
             {% endblock %}
             """
        to.save()

    def setUpAjaxLogin(self):
        if(self.good_version == -1):
             to, created = TemplateOverride.objects.get_or_create(name='index.html', version=1)
        else:
             to = TemplateOverride.objects.filter(name='index.html')[0]
        to.content = """
             {% extends "elements/html" %}

             {% block body %}
             {% include "users/loginbox_ajax.html" %}
             {% endblock %}
             """
        to.save()

    def test_csrf_delete(self):
        # First set up and test AJAX login
        self.setUpAjaxLogin()

        self.open_url("/")
        try_ajax_login(self, "student", "student")
        self.failUnless(self.is_text_present('Student Student'))
        logout(self)

        self.delete_cookie("csrftoken")

        try_ajax_login(self, "student", "student")
        self.failUnless(self.is_text_present('Please log in to access program registration'))
        logout(self)

        try_ajax_login(self, "student", "student")
        self.failUnless(self.is_text_present('Student Student'))
        logout(self)


        # Now set up and test normal login
        self.setUpNormalLogin()
        self.open_url("/") # Load index

        try_normal_login(self, "student", "student")
        self.failUnless(self.is_text_present('Student Student'))
        logout(self)

        self.delete_cookie("csrftoken")

        try_normal_login(self, "student", "student")
        self.failUnless(self.is_text_present('Student Student'))
        logout(self)
