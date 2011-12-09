from django_selenium.testcases import SeleniumTestCase
from esp.users.views.make_admin import make_user_admin
from esp.settings import VARNISH_PORT
from esp.datatree.models import GetNode

class TestQsdCachePurging(SeleniumTestCase):
    def setUp(self):
        SeleniumTestCase.setUp(self)

        # Make our users
        self.admin_user, created = ESPUser.objects.get_or_create(username='admin', first_name='Harry', last_name='Alborez')
        self.admin_user.set_password('password')
        make_user_admin(self.admin_user)
        self.qsd_user, created = ESPUser.objects.get_or_create(username='qsd', first_name='Aylik', last_name='Kewesd')
        self.qsd_user.set_password('password')
        self.qsd_user.userbit_set.add(UserBit(verb = GetNode('V/Administer/Edit/QSD'), qsc = GetNode('Q'), true))
        self.qsd_user.save()
        self.unpriv_user, created = ESPUser.objects.get_or_create(username='unpriv', first_name='Angry', last_name='Parent')
        self.unpriv_user.set_password('password')
        self.unpriv_user.save()

    def test_qsd_cache_purging(self):
        self.testserver_port = VARNISH_PORT
        self.open_url("SOMETHING")
        self.testserver_port = 8000 # Find where this number is actually stored
