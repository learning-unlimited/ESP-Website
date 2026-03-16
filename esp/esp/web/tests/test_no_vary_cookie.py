import difflib

from django.test.client import Client

from esp.program.tests import ProgramFrameworkTest
from esp.web.models import default_navbarcategory


class NoVaryOnCookieTest(ProgramFrameworkTest):
    """
    The "Vary: Cookie" header should not be set on selected views.
    """

    url = "/learn/TestProgram/2222_Summer/"

    def testQSD(self):
        c = Client()
        res = c.get(self.url + "index.html")

        self.assertEqual(res.status_code, 200)
        self.assertTrue("Vary" not in res or "Cookie" not in res["Vary"])
        logged_out_content = res.content.decode("UTF-8")

        c.login(username=self.admins[0], password="password")
        res = c.get(self.url + "index.html")

        self.assertEqual(res.status_code, 200)
        self.assertTrue("Vary" not in res or "Cookie" not in res["Vary"])
        logged_in_content = res.content.decode("UTF-8")

        self.assertEqual(
            "\n".join(
                difflib.context_diff(
                    logged_out_content.split("\n"),
                    logged_in_content.split("\n"),
                )
            ),
            "",
        )

    def testCatalog(self):
        c = Client()
        res = c.get(self.url + "catalog")

        self.assertEqual(res.status_code, 200)
        self.assertTrue("Vary" not in res or "Cookie" not in res["Vary"])
        logged_out_content = res.content.decode("UTF-8")

        c.login(username=self.admins[0], password="password")
        res = c.get(self.url + "catalog")

        self.assertEqual(res.status_code, 200)
        self.assertTrue("Vary" not in res or "Cookie" not in res["Vary"])
        logged_in_content = res.content.decode("UTF-8")

        self.assertEqual(
            "\n".join(
                difflib.context_diff(
                    logged_out_content.split("\n"),
                    logged_in_content.split("\n"),
                )
            ),
            "",
        )

    def setUp(self):
        super().setUp()

        from esp.qsd.models import QuasiStaticData

        qsd_rec_new = QuasiStaticData()
        qsd_rec_new.name = "learn:index"
        qsd_rec_new.author = self.admins[0]
        qsd_rec_new.nav_category = default_navbarcategory()
        qsd_rec_new.content = "This is the content of the test QSD page"
        qsd_rec_new.title = "Test QSD page"
        qsd_rec_new.description = ""
        qsd_rec_new.keywords = ""
        qsd_rec_new.save()
