"""
Unit tests for the admin_config_banner templatetag.

Verifies staff-only visibility, correct URL rendering,
custom link text, default link text, and print-safe CSS class.

Related issue: #3690
"""

from django.test import TestCase, RequestFactory
from django.template import Context, Template
from django.contrib.auth.models import User


class AdminConfigBannerTagTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.staff_user = User.objects.create_user(
            username='staffperson',
            password='testpass123',
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username='regularuser',
            password='testpass123',
            is_staff=False,
        )

    def _render(self, user, url='/manage/programs/', link_text=None):
        if link_text:
            template_str = (
                '{%% load admin_tags %%}'
                '{%% admin_config_banner config_url="%s" link_text="%s" %%}'
            ) % (url, link_text)
        else:
            template_str = (
                '{%% load admin_tags %%}'
                '{%% admin_config_banner config_url="%s" %%}'
            ) % url

        request = self.factory.get('/')
        request.user = user
        t = Template(template_str)
        c = Context({'request': request})
        return t.render(c)

    def test_banner_shown_to_staff(self):
        """Staff users must see the admin config banner."""
        output = self._render(self.staff_user)
        self.assertIn('admin-config-banner', output)

    def test_banner_hidden_from_non_staff(self):
        """Non-staff users must not see the banner at all."""
        output = self._render(self.regular_user)
        self.assertNotIn('admin-config-banner', output)

    def test_correct_url_in_banner(self):
        """The banner link must point to the config_url passed in."""
        url = '/manage/myprogram/main'
        output = self._render(self.staff_user, url=url)
        self.assertIn(url, output)

    def test_custom_link_text_appears(self):
        """Custom link_text must appear in the rendered banner."""
        output = self._render(self.staff_user, link_text='Edit teacher reg fields')
        self.assertIn('Edit teacher reg fields', output)

    def test_default_link_text_used_when_none_given(self):
        """Default link text must render when no link_text is passed."""
        output = self._render(self.staff_user)
        self.assertIn('Want to edit this form?', output)

    def test_no_print_class_present(self):
        """Banner must carry the no-print class so it is hidden when printing."""
        output = self._render(self.staff_user)
        self.assertIn('no-print', output)