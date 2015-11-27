"""
Tests for the theme editor.
"""

import re
import os
import random

from django.conf import settings

from esp.users.models import ESPUser
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.themes.controllers import ThemeController
from esp.themes import settings as themes_settings

class ThemesTest(TestCase):

    def setUp(self):

        #   Create user to function as administrator
        new_admin, created = ESPUser.objects.get_or_create(username='qsd_admin')
        new_admin.set_password('password')
        new_admin.save()
        new_admin.makeRole('Administrator')
        self.admin = new_admin

        #   Redirect compiled CSS output to avoid disturbing installed setup
        self._css_file = themes_settings.COMPILED_CSS_FILE
        themes_settings.COMPILED_CSS_FILE = 'theme_compiled_test.css'

    def tearDown(self):

        #   Restore destination of compiled CSS output
        themes_settings.COMPILED_CSS_FILE = self._css_file

    def testAvailableThemes(self):
        """ Check that the ThemeController says we have the themes we expect to have. """

        tc = ThemeController()
        names_ref = ['barebones', 'circles', 'floaty', 'fruitsalad']
        names_tc = tc.get_theme_names()
        self.assertEqual(set(names_ref), set(names_tc))

    def testAuthentication(self):
        """ Check that each themes page is not available to an unprivileged user,
            but is available to an administrator. """

        urls = ['/themes/', '/themes/select/', '/themes/setup/', '/themes/customize/']
        self.client.logout()

        for url in urls:
            response = self.client.get(url)
            self.assertRedirects(response, '/accounts/login/?next=%s' % url)

        self.client.login(username=self.admin.username, password='password')
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

        self.client.logout()

    def testSelector(self):
        """ Check that theme selector functionality is working. """

        self.client.login(username=self.admin.username, password='password')

        #   Get a ThemeController for identifying available themes.
        tc = ThemeController()

        #   Get the home page (this is a fresh site) and make sure it has a link to the theme landing.
        response = self.client.get('/')
        self.assertTrue(len(re.findall(r'<a href="/themes.*?Configure site appearance.*?</a>', response.content, flags=re.DOTALL)) == 1)

        #   Go to the themes landing page and theme selector, make sure neither errors out.
        response = self.client.get('/themes/')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/themes/select/')
        self.assertEqual(response.status_code, 200)

        #   Test each theme that is available.
        for theme_name in tc.get_theme_names():
            #   Delete the theme_compiled.css file so we force a new one to be generated.
            css_filename = os.path.join(settings.MEDIA_ROOT, 'styles', themes_settings.COMPILED_CSS_FILE)
            if os.path.exists(css_filename):
                os.remove(css_filename)

            #   POST to the theme selector with our choice of theme
            response = self.client.post('/themes/select/', {'action': 'select', 'theme': theme_name})
            self.assertEqual(response.status_code, 200)

            #   Supply more settings if the theme asks for them.
            if '<form id="theme_setup_form"' in response.content:
                field_matches = re.findall(r'<(input id="\S+"|textarea).*?name="(\S+)".*?>', response.content, flags=re.DOTALL)
                #   This is the union of all the theme configuration settings that
                #   have a non-trivial form (e.g. key = value fails validation).
                settings_dict = {
                    'theme': theme_name,
                    'just_selected': 'True',
                    'front_page_style': 'bubblesfront.html',
                    'facebook_link': 'http://somehost.net',
                    'nav_structure': '[{"header": "header", "header_link": "/header_link/", "links": [{"link": "link1", "text": "text1"}]}]',
                }
                for entry in field_matches:
                    if entry[1] not in settings_dict:
                        #   Supply value = key if we do not already know what to say
                        settings_dict[entry[1]] = entry[1]

                #   If theme setup succeeded, we will be redirected to the landing page.
                response = self.client.post('/themes/setup/', settings_dict, follow=True)
                self.assertTrue(('http://testserver/themes/', 302) in response.redirect_chain)

            #   Check that the CSS stylesheet has been included in the page.
            self.assertTrue('/media/styles/theme_compiled.css' in response.content)

            #   Check that the CSS stylesheet has been compiled.
            self.assertTrue(os.path.exists(css_filename))
            self.assertTrue(len(open(css_filename).read()) > 1000)  #   Hacky way to check that content is substantial
            """
            #   The following code would validate the CSS syntax, but cssutils doesn't seem to
            #   support the fancy CSS techniques used by Bootstrap and LESS.
            parser = cssutils.CSSParser(raiseExceptions=True)
            parser.parseFile(css_filename)
            """

            #   Check that the template override is marked with the theme name.
            self.assertTrue(('<!-- Theme: %s -->' % theme_name) in response.content)

        #   Test that the theme can be cleared and the home page reverts.
        response = self.client.post('/themes/select/', {'action': 'clear'})
        response = self.client.get('/')
        self.assertTrue(len(re.findall(r'<a href="/themes.*?Configure site appearance.*?</a>', response.content, flags=re.DOTALL)) == 1)

        self.client.logout()

    def testEditor(self):
        """ Check that the theme editor backend functionality is working. """

        """
        TODO:
        -   Check that theme specific properties show up on the form
        -   Check load, save, delete modes as well as test
        """

        #   Log in as administrator and load the theme editor
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get('/themes/customize/')
        self.assertEqual(response.status_code, 200)

        #   Check that the "advanced" properties for all themes show up in the form
        #   (using ThemeController directly for theme switching, since testSelector()
        #   covers the Web interface)
        tc = ThemeController()
        theme_names = tc.get_theme_names()
        for theme_name in theme_names:
            variables_filename = os.path.join(settings.MEDIA_ROOT, 'esp', 'themes', 'theme_data', theme_name, 'variables.less')
            if os.path.exists(variables_filename):
                tc.clear_theme()
                tc.load_theme(theme_name)
                response = self.client.get('/themes/customize/')
                self.assertEqual(response.status_code, 200)
                variables = re.findall(r'@(\S+):\s+?(\S+);', open(variables_filename).read())
                for (varname, value) in variables:
                    self.assertTrue(len(re.findall(r'<input.*?name="%s".*?value="%s".*?>', response.content, flags=re.I)) > 0)

        #   Test that we can change a parameter and the right value appears in the stylesheet
        def verify_linkcolor(color_str):
            css_filename = os.path.join(settings.MEDIA_ROOT, 'styles', themes_settings.COMPILED_CSS_FILE)
            regexp = r'\n\s*?a\s*?{.*?color:\s*?%s;.*?}' % color_str
            self.assertTrue(len(re.findall(regexp, open(css_filename).read(), flags=(re.DOTALL | re.I))) == 1)

        color_str1 = '#%06X' % random.randint(0, 1 << 24)
        config_dict = {'apply': True, 'linkColor': color_str1}
        response = self.client.post('/themes/customize/', config_dict)
        self.assertEqual(response.status_code, 200)
        verify_linkcolor(color_str1)

        #   Test that we can save this setting, change it and re-load
        config_dict = {'save': True, 'linkColor': color_str1, 'saveThemeName': 'save_test'}
        response = self.client.post('/themes/customize/', config_dict)
        self.assertEqual(response.status_code, 200)

        color_str2 = '#%06X' % random.randint(0, 1 << 24)
        config_dict = {'apply': True, 'linkColor': color_str2}
        response = self.client.post('/themes/customize/', config_dict)
        self.assertEqual(response.status_code, 200)
        verify_linkcolor(color_str2)

        config_dict = {'load': True, 'loadThemeName': 'save_test'}
        response = self.client.post('/themes/customize/', config_dict)
        self.assertEqual(response.status_code, 200)
        verify_linkcolor(color_str1)

        #   We're done.  Log out.
        self.client.logout()
