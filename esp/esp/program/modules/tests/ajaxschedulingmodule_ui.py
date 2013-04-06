from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from selenium.webdriver.firefox.webdriver import WebDriver

class AJAXSchedulingModuleUITest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        # Set up the program -- we want to be sure of these parameters
        kwargs.update({
            'num_rooms': 4,
            'num_timeslots': 4, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 3, 'classes_per_teacher': 2, 'sections_per_class': 1
            })
        super(AJAXSchedulingModuleUITest, self).setUp(*args, **kwargs)
        self.browser = WebDriver()

    def tearDown(self):
        self.browser.quit()

    def testAJAX(self):
        self.browser.get(self.live_server_url + '/manage/' + self.program.get_url_base() + '/ajax_scheduling')
        self.failUnless(True, "hi")

        
