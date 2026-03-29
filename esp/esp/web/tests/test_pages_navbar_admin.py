import re

from django.contrib.auth.models import User
from django.test import RequestFactory
from django.test.client import Client

from esp.admin import admin_site
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.utils.models import TemplateOverride
from esp.web.admin import NavBarCategoryAdmin
from esp.web.models import NavBarCategory, NavBarEntry


class PageTest(TestCase):
    """Validate common hard-coded flatpages."""

    def assertStringContains(self, string, contents):
        if contents not in string:
            self.fail("'%s' not in '%s'" % (contents, string))

    def assertNotStringContains(self, string, contents):
        if contents in string:
            self.fail("'%s' are in '%s' and shouldn't be" % (contents, string))

    def testHomePage(self):
        c = Client()
        response = c.get("/")

        self.assertEqual(response.status_code, 200)
        content = str(response.content, encoding="UTF-8")
        self.assertStringContains(content, "<html")
        self.assertNotStringContains(
            content,
            "You're seeing this error because you have <code>DEBUG = True</code>",
        )


class NavbarTest(TestCase):
    def get_navbar_titles(self, path="/"):
        response = self.client.get(path)

        navbaritem_re = re.compile(r'<li class="divsecondarynavlink (?:indent)?">\s+(.*)\s+</li>')
        return re.findall(navbaritem_re, str(response.content, encoding="UTF-8"))

    def navbars_enabled(self):
        qs = TemplateOverride.objects.filter(name="main.html").order_by("-id")
        if qs.exists() and qs[0].content.find("{% navbar_gen") < 0:
            return False
        return True

    def testNavbarBehavior(self):
        home_category, _created = NavBarCategory.objects.get_or_create(name="home")

        if not self.navbars_enabled():
            return

        NavBarEntry.objects.all().delete()
        self.assertTrue(self.get_navbar_titles("/") == [])

        n1 = NavBarEntry(category=home_category, sort_rank=0, text="NavBar1", indent=False)
        n1.save()
        self.assertTrue(self.get_navbar_titles("/") == ["NavBar1"])

        n1.text = "NavBar1A"
        n1.save()
        self.assertTrue(self.get_navbar_titles("/") == ["NavBar1A"])

        n2 = NavBarEntry(category=home_category, sort_rank=10, text="NavBar2", indent=False)
        n2.save()
        self.assertTrue(self.get_navbar_titles("/") == ["NavBar1A", "NavBar2"])

        n1.sort_rank = 20
        n1.save()
        self.assertTrue(self.get_navbar_titles("/") == ["NavBar2", "NavBar1A"])


class NavBarAdminDeletionTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="password",
        )

        self.default_category = NavBarCategory.objects.create(
            name="default",
            long_explanation="Default category",
        )

        self.admin = NavBarCategoryAdmin(NavBarCategory, admin_site)

    def test_default_category_cannot_be_deleted(self):
        request = self.factory.get("/")
        request.user = self.user

        has_permission = self.admin.has_delete_permission(request, obj=self.default_category)
        self.assertFalse(has_permission)

    def test_non_default_category_can_be_deleted(self):
        other = NavBarCategory.objects.create(
            name="home",
            long_explanation="Home category",
        )

        request = self.factory.get("/")
        request.user = self.user

        has_permission = self.admin.has_delete_permission(request, obj=other)
        self.assertTrue(has_permission)
