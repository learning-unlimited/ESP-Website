"""
Tests for the theme editor.
"""

import os
import random
import re
import shutil
import tempfile
import unittest.mock as mock

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation

from esp.users.models import ESPUser
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.tagdict.models import Tag
from esp.themes.controllers import ThemeController
from esp.themes import settings as themes_settings
from io import open

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
        worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'main')
        themes_settings.COMPILED_CSS_FILE = f'theme_compiled_test_{worker_id}.css'

    def tearDown(self):

        #   Restore destination of compiled CSS output
        themes_settings.COMPILED_CSS_FILE = self._css_file

    def testAvailableThemes(self):
        """ Check that the ThemeController says we have the themes we expect to have. """

        tc = ThemeController()
        names_ref = ['barebones', 'bigpicture', 'circles', 'floaty', 'fruitsalad', 'droplets']
        names_tc = tc.get_theme_names()
        self.assertEqual(set(names_ref), set(names_tc))

    def testAuthentication(self):
        """ Check that each themes page is not available to an unprivileged user,
            but is available to an administrator. """

        urls = ['/themes/', '/themes/select/', '/themes/setup/', '/themes/customize/']
        self.client.logout()

        for url in urls:
            response = self.client.get(url)
            self.assertRedirects(response, f'/accounts/login/?next={url}')

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
        self.assertTrue(len(re.findall(r'<a href="/themes.*?Configure site appearance.*?</a>',
                                       str(response.content, encoding='UTF-8'), flags=re.DOTALL)) == 1)

        #   Go to the themes landing page and theme selector, make sure neither errors out.
        response = self.client.get('/themes/')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/themes/select/')
        self.assertEqual(response.status_code, 200)

        # Move the existing images dir out of the way, so we don't conflict
        # with it (either what the user has there, or between themes).
        # TODO(benkraft): Do the same for styles and scripts, although in
        # practice conflicts there are less likely.
        # TODO(benkraft): This is a super hacky way to do things!  Instead we
        # should be doing all these tests in some sort of tmpdir to avoid
        # touching anything of the user's.
        images_dir = os.path.join(settings.MEDIA_ROOT, 'images', 'theme')
        # Really we should use a tempdir, but on Docker it may be on a
        # different file system, which causes problems, so we do a hackier
        # thing instead.
        images_backup_dir = os.path.join(settings.MEDIA_ROOT, 'images',
                                         'theme_backup_for_tests')
        if os.path.exists(images_dir):
            os.rename(images_dir, images_backup_dir)

        try:
            #   Test each theme that is available.
            for theme_name in tc.get_theme_names():
                #   Delete the theme_compiled.css file so we force a new one to be generated.
                css_filename = os.path.join(settings.MEDIA_ROOT, 'styles', themes_settings.COMPILED_CSS_FILE)
                if os.path.exists(css_filename):
                    os.remove(css_filename)
                # Clobber any stray theme images dir, to avoid conflicts.
                # Note that we've already backed up any one the user had
                # created, above.
                if os.path.exists(images_dir):
                    shutil.rmtree(images_dir)

                # Make sure there won't be any conflicts between this theme and
                # existing files -- since they would cause harder-to-understand
                # errors later on.
                self.assertFalse(tc.check_local_modifications(theme_name))

                #   POST to the theme selector with our choice of theme
                response = self.client.post('/themes/select/', {'action': 'select', 'theme': theme_name})
                self.assertEqual(response.status_code, 200)

                #   Supply more settings if the theme asks for them.
                if '<form id="theme_setup_form"' in str(response.content, encoding='UTF-8'):
                    field_matches = re.findall(r'<(input id="\S+"|textarea).*?name="(\S+)".*?>',
                                               str(response.content, encoding='UTF-8'), flags=re.DOTALL)
                    #   This is the union of all the theme configuration settings that
                    #   have a non-trivial form (e.g. key = value fails validation).
                    settings_dict = {
                        'theme': theme_name,
                        'full_group_name': 'themetest',
                        'titlebar_prefix': 'themetest',
                        'welcome_message': 'themetest',
                        'title_text': 'themetest',
                        'subtitle_text': 'themetest',
                        'contact_info': 'themetest',
                        'just_selected': 'True',
                        'show_email': 'True',
                        'show_group_name': 'True',
                        'front_page_style': 'bubblesfront.html',
                        'facebook_link': 'http://somehost.net',
                        'faq_link': '/faq.html',
                        'nav_structure': '[{"header": "header", "header_link": "/header_link/", "links": [{"link": "link1", "text": "text1"}]}]',
                        'contact_links': '[{"link": "link1", "text": "text1"}]',
                    }
                    for entry in field_matches:
                        if entry[1] not in settings_dict:
                            #   Supply value = key if we do not already know what to say
                            settings_dict[entry[1]] = entry[1]

                    #   If theme setup succeeded, we will be redirected to the landing page.
                    response = self.client.post('/themes/setup/', settings_dict, follow=True)
                    self.assertTrue(('/themes/', 302) in response.redirect_chain)

                #   Check that the CSS stylesheet has been included in the page.
                self.assertTrue('/media/styles/theme_compiled.css' in str(response.content, encoding='UTF-8'))

                #   Check that the CSS stylesheet has been compiled.
                self.assertTrue(os.path.exists(css_filename))
                self.assertTrue(len(open(css_filename).read()) > 1000)  #   Hacky way to check that content is substantial

                #   Check that the template override is marked with the theme name.
                self.assertTrue((f'<!-- Theme: {theme_name} -->') in str(response.content, encoding='UTF-8'))

            self.client.logout()

        finally:
            # Restore the backed up images dir.
            if os.path.exists(images_dir):
                shutil.rmtree(images_dir)
            if os.path.exists(images_backup_dir):
                os.rename(images_backup_dir, images_dir)

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
            theme_data_dir = os.path.join(settings.PROJECT_ROOT, 'esp', 'themes', 'theme_data', theme_name)
            variables_filename = os.path.join(theme_data_dir, 'scss', 'variables.scss')
            var_pattern = r'\$([a-zA-Z0-9_]+):\s+?(\S+);'
            if os.path.exists(variables_filename):
                # Themes with a config form need template settings (see testSelector).
                if tc.get_config_form_class(theme_name) is not None:
                    continue
                tc.clear_theme()
                tc.load_theme(theme_name)
                response = self.client.get('/themes/customize/')
                self.assertEqual(response.status_code, 200)
                variables = re.findall(var_pattern, open(variables_filename).read())
                for (varname, value) in variables:
                    # Derived expressions (e.g. darken()) are not exposed as simple editor inputs.
                    if '(' in value:
                        continue
                    self.assertTrue(len(re.findall(rf'<input[^>]*\bname="{re.escape(varname)}"',
                                    str(response.content, encoding='UTF-8'), flags=re.I)) > 0,
                                    f'Missing editor input for {theme_name} variable {varname}')

        #   Test that we can change a parameter and the right value appears in the stylesheet.
        #   Bootstrap 5 exposes $link-color as the --bs-link-color CSS custom property in :root,
        #   so we check for the custom property rather than a direct `a { color: ... }` rule.
        def verify_linkcolor(color_str, absent_color_str=None):
            css_filename = os.path.join(settings.MEDIA_ROOT, 'styles', themes_settings.COMPILED_CSS_FILE)
            regexp = rf'--bs-link-color:\s*{re.escape(color_str)};'
            with open(css_filename) as f:
                css = f.read()
            self.assertGreaterEqual(len(re.findall(regexp, css, flags=re.I)), 1,
                                    f'Expected --bs-link-color: {color_str} in compiled CSS')
            if absent_color_str is not None:
                #   Recompiling must replace the old declaration, not append to it.
                old_regexp = rf'--bs-link-color:\s*{re.escape(absent_color_str)};'
                self.assertEqual(len(re.findall(old_regexp, css, flags=re.I)), 0,
                                 f'Stale --bs-link-color: {absent_color_str} still in compiled CSS')

        #   The editor uses Post/Redirect/Get, so each POST returns a 302 to the
        #   editor; follow=True lands on the resulting 200 GET (and the CSS is
        #   compiled during the POST, before the redirect).
        color_str1 = '#%06X' % random.randint(0, 1 << 24)
        config_dict = {'apply': True, 'linkColor': color_str1}
        response = self.client.post('/themes/customize/', config_dict, follow=True)
        self.assertEqual(response.status_code, 200)
        verify_linkcolor(color_str1)

        #   Test that we can save this setting, change it, and reload
        config_dict = {'save': True, 'linkColor': color_str1, 'saveThemeName': 'save_test'}
        response = self.client.post('/themes/customize/', config_dict, follow=True)
        self.assertEqual(response.status_code, 200)

        color_str2 = '#%06X' % random.randint(0, 1 << 24)
        config_dict = {'apply': True, 'linkColor': color_str2}
        response = self.client.post('/themes/customize/', config_dict, follow=True)
        self.assertEqual(response.status_code, 200)
        verify_linkcolor(color_str2, absent_color_str=color_str1)

        config_dict = {'load': True, 'loadThemeName': 'save_test'}
        response = self.client.post('/themes/customize/', config_dict, follow=True)
        self.assertEqual(response.status_code, 200)
        verify_linkcolor(color_str1)

        #   We're done.  Log out.
        self.client.logout()

    def testEditorBootswatchApplyAndSaveLoad(self):
        """ PR #5862 review comments #2 and #3:
        - Switching the Bootswatch dropdown and editing a field in the same
          "Apply" must apply both changes together, not drop the field edit.
        - Saving a customization while a Bootswatch theme is active must
          persist that theme, so Loading the customization later restores it
          regardless of whichever Bootswatch theme happens to be active. """
        tc = ThemeController()
        scss_themes = [n for n in tc.get_theme_names() if tc.has_scss(n)]
        bw_themes = tc.get_bootswatch_themes()
        if not scss_themes or not bw_themes:
            self.skipTest('No SCSS theme / Bootswatch package available')
        theme_name = scss_themes[0]
        bw_a = bw_themes[0]
        bw_b = bw_themes[1] if len(bw_themes) > 1 else bw_themes[0]

        tc.clear_theme()
        tc.load_theme(theme_name)
        Tag.unSetTag('bootswatch_theme')

        self.client.login(username=self.admin.username, password='password')
        try:
            #   Comment #2: switch the Bootswatch theme AND edit a field in
            #   one Apply -- both must take effect.
            custom_color = '#%06X' % random.randint(0, 1 << 24)
            config_dict = {'apply': True, 'bootswatch_theme': bw_a, 'linkColor': custom_color}
            response = self.client.post('/themes/customize/', config_dict, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Tag.getTag('bootswatch_theme', default=''), bw_a)
            self.assertEqual(tc.get_current_params().get('linkColor'), custom_color)

            #   Comment #3: saving while bw_a is active persists it in the
            #   customization file; switching the live tag away and then
            #   Loading that customization must restore bw_a.
            config_dict = {'save': True, 'bootswatch_theme': bw_a, 'linkColor': custom_color,
                            'saveThemeName': 'bootswatch_save_test'}
            response = self.client.post('/themes/customize/', config_dict, follow=True)
            self.assertEqual(response.status_code, 200)

            Tag.setTag('bootswatch_theme', value=bw_b)
            config_dict = {'load': True, 'loadThemeName': 'bootswatch_save_test'}
            response = self.client.post('/themes/customize/', config_dict, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Tag.getTag('bootswatch_theme', default=''), bw_a)
        finally:
            self.client.logout()
            try:
                tc.delete_customizations('bootswatch_save_test')
            except OSError:
                pass
            Tag.unSetTag('bootswatch_theme')

    def testRecompileThemeCreatesMissingCustomization(self):
        """ Check that recompile_theme does not crash and leaves the system in a consistent state
            by creating the customization file if it is missing. """
        import tempfile
        import uuid

        tc = ThemeController()
        tc.clear_theme()
        tc.load_theme('barebones')

        # Use a temporary directory + unique filename to avoid dirtying the working tree
        original_themes_dir = themes_settings.themes_dir
        themes_settings.themes_dir = tempfile.mkdtemp()
        fake_customization_name = f'test_missing_{uuid.uuid4().hex}'
        customization_file = os.path.join(themes_settings.themes_dir, f'{fake_customization_name}.less')

        tc.set_current_customization(fake_customization_name)

        try:
            # This shouldn't raise FileNotFoundError; it should catch it and create the file
            tc.recompile_theme(customization_name=fake_customization_name)

            # The file should be created now
            self.assertTrue(os.path.exists(customization_file))
        finally:
            # Cleanup tag and temporary files
            tc.unset_current_customization()
            shutil.rmtree(themes_settings.themes_dir, ignore_errors=True)
            themes_settings.themes_dir = original_themes_dir


class ScssPipelineTest(TestCase):
    """Unit tests for the Bootstrap 5 SCSS theme compilation pipeline."""

    def setUp(self):
        self._css_file = themes_settings.COMPILED_CSS_FILE
        themes_settings.COMPILED_CSS_FILE = 'theme_compiled_test.css'
        self.tc = ThemeController()
        self.css_filename = os.path.join(settings.MEDIA_ROOT, 'styles', themes_settings.COMPILED_CSS_FILE)

    def tearDown(self):
        themes_settings.COMPILED_CSS_FILE = self._css_file
        if os.path.exists(self.css_filename):
            os.remove(self.css_filename)

    def test_all_themes_use_scss_pipeline(self):
        """Every bundled theme should have a scss/ directory (Bootstrap 5 pipeline)."""
        for theme_name in self.tc.get_theme_names():
            self.assertTrue(
                self.tc.has_scss(theme_name),
                f'{theme_name} is missing scss/ — expected Bootstrap 5 SCSS pipeline',
            )

    def test_get_scss_names_includes_theme_editor_sources(self):
        """get_scss_names() includes theme-editor and theme SCSS before Bootstrap import."""
        names = [f.replace('\\', '/') for f in self.tc.get_scss_names('barebones')]
        self.assertTrue(
            any('theme_editor/scss/variables_custom.scss' in f for f in names),
            'variables_custom.scss should be included',
        )
        self.assertTrue(
            any('theme_data/barebones/scss/main.scss' in f for f in names),
            'theme main.scss should be included',
        )
        self.assertFalse(
            any('.less' in f for f in names),
            'Legacy LESS sources should not appear in SCSS pipeline',
        )

    def test_compile_css_produces_bs5_markers(self):
        """compile_css() output contains BS5 markers and no BS3 glyphicon class."""
        self.tc.compile_css('barebones', {}, self.css_filename)
        with open(self.css_filename) as f:
            css = f.read()
        self.assertGreater(len(css), 10000)
        self.assertIn('.navbar-toggler', css, 'Missing .navbar-toggler — BS5 not compiling')
        self.assertIn('.card', css, 'Missing .card — BS5 not compiling')
        self.assertIn('.bi', css, 'Missing .bi — Bootstrap Icons not included')
        self.assertNotIn('.glyphicon', css, '.glyphicon present — BS3 leaked into BS5 output')

    def test_get_variable_defaults_roundtrip(self):
        """get_variable_defaults() compiles and returns a non-empty dict for every theme."""
        for theme_name in self.tc.get_theme_names():
            defaults = self.tc.get_variable_defaults(theme_name)
            self.assertIsInstance(defaults, dict)
            self.assertGreater(len(defaults), 0, f'{theme_name}: get_variable_defaults() returned empty dict')

    def test_get_bootswatch_themes_returns_sorted_list(self):
        """get_bootswatch_themes() returns a sorted list; empty list when npm package absent."""
        themes_list = self.tc.get_bootswatch_themes()
        self.assertIsInstance(themes_list, list)
        self.assertEqual(themes_list, sorted(themes_list), 'Bootswatch theme list must be sorted')

    def test_bootswatch_themes_have_required_scss_files(self):
        """Each discovered Bootswatch theme has _variables.scss and _bootswatch.scss (Bootswatch 5 SCSS layout)."""
        bootswatch_dist = os.path.normpath(os.path.join(
            themes_settings.scss_dir, '..', 'node_modules', 'bootswatch', 'dist'
        ))
        for name in self.tc.get_bootswatch_themes():
            self.assertTrue(
                os.path.exists(os.path.join(bootswatch_dist, name, '_variables.scss')),
                f'bootswatch/dist/{name}/_variables.scss missing'
            )
            self.assertTrue(
                os.path.exists(os.path.join(bootswatch_dist, name, '_bootswatch.scss')),
                f'bootswatch/dist/{name}/_bootswatch.scss missing'
            )

    def test_compile_css_with_scss_bootswatch_produces_valid_output(self):
        """compile_css() with a Bootswatch 5 skin on an SCSS theme compiles to non-trivial CSS."""
        scss_themes = [n for n in self.tc.get_theme_names() if self.tc.has_scss(n)]
        if not scss_themes:
            self.skipTest('No SCSS themes available')
        themes_list = self.tc.get_bootswatch_themes()
        if not themes_list:
            self.skipTest('Bootswatch 5 npm package not installed')
        self.tc.compile_css(scss_themes[0], {}, self.css_filename, bootswatch_theme=themes_list[0])
        with open(self.css_filename) as f:
            css = f.read()
        self.assertGreater(len(css), 10000)
        self.assertIn('--bs-', css, 'Compiled CSS should contain Bootstrap 5 custom properties')

    def test_compile_css_raises_for_unknown_explicit_bootswatch(self):
        """compile_css() raises ValueError when an unknown Bootswatch skin is passed explicitly."""
        scss_themes = [n for n in self.tc.get_theme_names() if self.tc.has_scss(n)]
        if not scss_themes:
            self.skipTest('No SCSS themes available')
        with self.assertRaises(ValueError):
            self.tc.compile_css(scss_themes[0], {}, self.css_filename,
                                bootswatch_theme='no-such-bootswatch-skin')

    def test_compile_css_raises_for_theme_without_scss(self):
        """compile_css() rejects themes that lack SCSS sources."""
        with self.assertRaises(ValueError):
            self.tc.compile_css('nonexistent_theme_xyz', {}, self.css_filename)

    def test_get_variable_defaults_raises_for_theme_without_scss(self):
        """get_variable_defaults() rejects known theme names that lack SCSS."""
        # Force a name that is in _ALL_THEMES but not _SCSS_THEMES by patching.
        import esp.themes.controllers as controllers_mod
        with mock.patch.object(controllers_mod, '_ALL_THEMES', frozenset({'fake_less_only'})):
            with mock.patch.object(controllers_mod, '_SCSS_THEMES', frozenset()):
                with self.assertRaises(ValueError) as ctx:
                    self.tc.get_variable_defaults('fake_less_only')
        self.assertIn('no SCSS sources', str(ctx.exception))


class RecompileThemeCommandTest(TestCase):
    """recompile_theme management command must resolve names before retry."""

    def test_retry_reuses_theme_and_customization_resolved_up_front(self):
        from esp.themes.management.commands.recompile_theme import Command

        tc = mock.Mock()
        tc.get_current_theme.return_value = 'droplets'
        tc.get_current_customization.return_value = 'my_custom'
        tc.recompile_theme.side_effect = [RuntimeError('first failure'), None]

        with mock.patch('esp.themes.controllers.ThemeController', return_value=tc):
            Command().handle()

        self.assertEqual(tc.recompile_theme.call_count, 2)
        for call_args in tc.recompile_theme.call_args_list:
            self.assertEqual(call_args.kwargs['theme_name'], 'droplets')
            self.assertEqual(call_args.kwargs['customization_name'], 'my_custom')
        # Names are read once before any attempt (not again on retry).
        tc.get_current_theme.assert_called_once()
        tc.get_current_customization.assert_called_once()


class EspOverriddenBehaviorTest(TestCase):
    """Guarantees around the $esp-overridden set when a Bootswatch theme is
    active: fields matching the displayed (Bootswatch-derived) default must
    not become overrides, genuinely changed fields must, and switching themes
    must not carry stale overrides forward. (Raised in PR review as untested.)"""

    def setUp(self):
        self._css_file = themes_settings.COMPILED_CSS_FILE
        themes_settings.COMPILED_CSS_FILE = 'theme_compiled_test.css'
        self.tc = ThemeController()
        self.css_filename = os.path.join(settings.MEDIA_ROOT, 'styles', themes_settings.COMPILED_CSS_FILE)
        scss_themes = [n for n in self.tc.get_theme_names() if self.tc.has_scss(n)]
        if not scss_themes:
            self.skipTest('No SCSS themes available')
        self.theme_name = scss_themes[0]
        bw_themes = self.tc.get_bootswatch_themes()
        if not bw_themes:
            self.skipTest('Bootswatch 5 npm package not installed')
        self.bw_theme = bw_themes[0]
        self.tc.load_theme(self.theme_name)
        Tag.setTag('bootswatch_theme', value=self.bw_theme)

    def tearDown(self):
        themes_settings.COMPILED_CSS_FILE = self._css_file
        if os.path.exists(self.css_filename):
            os.remove(self.css_filename)
        Tag.unSetTag('bootswatch_theme')
        Tag.setTag('current_theme_params', value='{}')

    def test_effective_defaults_include_bootswatch_derivation(self):
        """get_effective_defaults() must be overlaid with the Bootswatch theme's
        derived colours, not just the raw SCSS defaults."""
        bw_vars = self.tc.get_bootswatch_esp_vars(self.bw_theme, esp_theme=self.theme_name)
        effective = self.tc.get_effective_defaults(self.theme_name, self.bw_theme)
        for key, val in bw_vars.items():
            self.assertEqual(effective[key], val)

    def test_unchanged_prefilled_values_do_not_become_overrides(self):
        """Submitting the form exactly as displayed (Bootswatch-derived
        defaults, nothing edited by the admin) must not persist any override."""
        effective = self.tc.get_effective_defaults(self.theme_name, self.bw_theme)
        self.tc.customize_theme(dict(effective))
        self.assertEqual(self.tc.get_current_params(), {})

    def test_genuinely_changed_value_is_persisted_as_override(self):
        """A field the admin actually edited away from the displayed default
        must be persisted, and only that field."""
        effective = dict(self.tc.get_effective_defaults(self.theme_name, self.bw_theme))
        effective['linkColor'] = '#123456'
        self.tc.customize_theme(effective)
        saved = self.tc.get_current_params()
        self.assertEqual(saved, {'linkColor': '#123456'})

    def test_switching_bootswatch_theme_does_not_carry_over_stale_overrides(self):
        """Save cleanly under theme A, then switch to theme B and resubmit the
        (dropdown-updated) form untouched: theme B's override set must be
        empty, not polluted with theme A's leftover colours."""
        effective_a = self.tc.get_effective_defaults(self.theme_name, self.bw_theme)
        self.tc.customize_theme(dict(effective_a))
        self.assertEqual(self.tc.get_current_params(), {})

        other_bw_themes = [t for t in self.tc.get_bootswatch_themes() if t != self.bw_theme]
        if not other_bw_themes:
            self.skipTest('Only one Bootswatch theme installed')
        theme_b = other_bw_themes[0]
        Tag.setTag('bootswatch_theme', value=theme_b)
        effective_b = self.tc.get_effective_defaults(self.theme_name, theme_b)
        self.tc.customize_theme(dict(effective_b))
        self.assertEqual(self.tc.get_current_params(), {})


class SafeCustomizationPathTest(TestCase):
    """Tests for the _safe_customization_path security helper."""

    def setUp(self):
        self.tc = ThemeController()
        # Use a temporary directory so tests don't touch working tree
        self._original_themes_dir = themes_settings.themes_dir
        self._tmpdir = tempfile.mkdtemp()
        themes_settings.themes_dir = self._tmpdir

    def tearDown(self):
        themes_settings.themes_dir = self._original_themes_dir
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_normal_name_returns_path_inside_themes_dir(self):
        """A simple alphanumeric name should resolve inside themes_dir."""
        path = self.tc._safe_customization_path('my_theme')
        self.assertTrue(path.startswith(os.path.realpath(self._tmpdir) + os.sep))
        self.assertTrue(path.endswith('.less'))

    def test_traversal_with_dotdot_raises(self):
        """Names containing '..' that escape themes_dir must raise."""
        with self.assertRaises(SuspiciousFileOperation):
            self.tc._safe_customization_path('../../etc/passwd')

    def test_absolute_path_raises(self):
        """An absolute path like '/tmp/evil' must raise."""
        with self.assertRaises(SuspiciousFileOperation):
            self.tc._safe_customization_path('/tmp/evil')

    def test_name_with_slash_raises(self):
        """A name with embedded slashes that escapes themes_dir must raise."""
        with self.assertRaises(SuspiciousFileOperation):
            self.tc._safe_customization_path('subdir/../../../etc/shadow')


class FindScssVariablesSecurityTest(TestCase):
    """Tests for find_scss_variables path-safety validation."""

    def setUp(self):
        self.tc = ThemeController()

    def test_find_scss_variables_rejects_path_outside_safe_roots(self):
        """find_scss_variables silently skips filenames that resolve outside safe roots."""
        outside_path = '/tmp/evil.scss'
        with mock.patch.object(self.tc, 'get_scss_names', return_value=[outside_path]):
            with self.assertLogs('esp.themes.controllers', level='WARNING') as cm:
                result = self.tc.find_scss_variables('barebones', flat=True)
        self.assertEqual(result, {})
        self.assertTrue(any('rejecting' in msg for msg in cm.output))

    def test_get_scss_names_unknown_theme_returns_global_files_only(self):
        """get_scss_names for an unknown theme returns only the global SCSS files."""
        names = self.tc.get_scss_names('nonexistent_theme_xyz')
        self.assertTrue(all('theme_data' not in f for f in names),
                        'Unknown theme should not produce theme_data/ entries')
        self.assertTrue(any('variables_custom.scss' in f for f in names))

    def test_find_theme_variables_uses_scss_pipeline(self):
        """find_theme_variables always delegates to find_scss_variables."""
        with mock.patch.object(self.tc, 'find_scss_variables', return_value={'x': '1'}) as mock_scss:
            result = self.tc.find_theme_variables('barebones')
        mock_scss.assert_called_once()
        self.assertEqual(result, {'x': '1'})


class SanitizeScssValueTest(TestCase):
    """Tests for _sanitize_scss_value injection guard."""

    def setUp(self):
        from esp.themes.controllers import _sanitize_scss_value
        self._fn = _sanitize_scss_value

    def test_accepts_plain_color(self):
        self.assertEqual(self._fn('color', '#ff0000'), '#ff0000')

    def test_accepts_px_value(self):
        self.assertEqual(self._fn('font-size', '14px'), '14px')

    def test_rejects_at_import(self):
        with self.assertLogs('esp.themes.controllers', level='WARNING'):
            self.assertIsNone(self._fn('color', '@import "evil"'))

    def test_rejects_url(self):
        with self.assertLogs('esp.themes.controllers', level='WARNING'):
            self.assertIsNone(self._fn('bg', 'url(/evil)'))

    def test_rejects_semicolon(self):
        with self.assertLogs('esp.themes.controllers', level='WARNING'):
            self.assertIsNone(self._fn('color', 'red; background: evil'))

    def test_rejects_braces(self):
        with self.assertLogs('esp.themes.controllers', level='WARNING'):
            self.assertIsNone(self._fn('color', '{color: red}'))


class CompileScssErrorPathTest(TestCase):
    """Tests for compile_scss error handling."""

    def setUp(self):
        self.tc = ThemeController()

    def test_compile_scss_raises_on_nonzero_returncode(self):
        """compile_scss raises ESPError_Log when the sass subprocess exits non-zero."""
        import unittest.mock as mock
        from esp.middleware.esperrormiddleware import ESPError_Log
        mock_proc = mock.Mock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = (b'', b'Error: bad scss')
        with mock.patch('esp.themes.controllers.subprocess.Popen', return_value=mock_proc):
            with self.assertRaises(ESPError_Log):
                self.tc.compile_scss('$broken: {;')


class GetVariableDefaultsUnknownThemeTest(TestCase):
    """Tests for get_variable_defaults fallback to barebones on unknown theme."""

    def setUp(self):
        self.tc = ThemeController()

    def test_unknown_theme_falls_back_to_barebones(self):
        """get_variable_defaults with an unknown name must not raise and must return a dict."""
        result = self.tc.get_variable_defaults('__nonexistent_xyz__')
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)


class EnsureThemeMediaTest(TestCase):
    """Tests for ThemeController.ensure_theme_media()."""

    def setUp(self):
        self.tc = ThemeController()
        self._tmpdir = tempfile.mkdtemp()
        self._orig_media = settings.MEDIA_ROOT
        settings.MEDIA_ROOT = self._tmpdir

    def tearDown(self):
        settings.MEDIA_ROOT = self._orig_media
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_file(self, rel, content=b'data'):
        path = os.path.join(self._tmpdir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(content)
        return path

    def test_missing_logo_is_copied_from_default(self):
        """Logo is copied from default_images when it does not exist yet."""
        self._write_file('default_images/theme/logo.png', b'reallogo')
        self.tc.ensure_theme_media()
        dest = os.path.join(self._tmpdir, 'images', 'theme', 'logo.png')
        self.assertTrue(os.path.exists(dest))

    def test_placeholder_logo_is_replaced(self):
        """Placeholder logo (matching MD5) is replaced with the default."""
        import hashlib
        from esp.themes.controllers import PLACEHOLDER_LOGO_MD5
        placeholder = b'placeholder'
        # Write a file whose MD5 matches PLACEHOLDER_LOGO_MD5 by patching the constant
        with mock.patch('esp.themes.controllers.PLACEHOLDER_LOGO_MD5',
                        hashlib.md5(placeholder).hexdigest()):
            self._write_file('images/theme/logo.png', placeholder)
            self._write_file('default_images/theme/logo.png', b'reallogo')
            self.tc.ensure_theme_media()
        dest = os.path.join(self._tmpdir, 'images', 'theme', 'logo.png')
        with open(dest, 'rb') as f:
            self.assertEqual(f.read(), b'reallogo')

    def test_non_placeholder_logo_is_kept(self):
        """An existing logo with a non-placeholder MD5 must not be overwritten."""
        self._write_file('images/theme/logo.png', b'customlogo')
        self._write_file('default_images/theme/logo.png', b'defaultlogo')
        self.tc.ensure_theme_media()
        dest = os.path.join(self._tmpdir, 'images', 'theme', 'logo.png')
        with open(dest, 'rb') as f:
            self.assertEqual(f.read(), b'customlogo')
