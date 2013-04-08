from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.tests import AJAXSchedulingModuleTest
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

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

    def loginAdmin(self, uname, pword):
        uname_el_id = "user"
        pword_el_id = "pass"
        submit_el_id = "gologin"
 
        # self.browser.find_element_by_id(uname_el_id).send_keys(uname)        
        # self.browser.find_element_by_id(pword_el_id).send_keys(pword)        
        # self.browser.find_element_by_id(submit_el_id).click()
        self.browser.get(self.live_server_url)
        
        e = WebDriverWait(self.browser, 10).until(
             lambda driver: self.browser.find_element_by_id(uname_el_id))
        e.send_keys(uname)
        e = WebDriverWait(self.browser, 10).until(
             lambda driver: self.browser.find_element_by_id(pword_el_id))
        e.send_keys(pword)
        e = WebDriverWait(self.browser, 10).until(
             lambda driver:    self.browser.find_element_by_id(submit_el_id))
        e.click()

    def testGetChangeLog(self):
        self.loginAdmin(self.admins[0].username, "password")
        self.browser.get(self.live_server_url + '/manage/' + self.program.getUrlBase() + '/ajax_scheduling')
        #schedule a class on the server
        
        #browser gets the change log
        
        #test that the class is actually scheduled
