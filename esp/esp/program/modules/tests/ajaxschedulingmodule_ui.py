from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
#from esp.program.modules.tests.ajaxschedulingmodule import AJAXSchedulingModuleTestBase
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

class AJAXSchedulingModuleUITest(ProgramFrameworkTest):#AJAXSchedulingModuleTestBase):
    def setUp(self, *args, **kwargs): 
         super(AJAXSchedulingModuleUITest, self).setUp(*args, **kwargs)
         self.browser = WebDriver()

    def tearDown(self):
        self.browser.quit()

    def loginAdminBrowser(self, uname, pword):
        uname_el_id = "user"
        pword_el_id = "pass"
        submit_el_id = "gologin"
 
        self.browser.get(self.live_server_url)
        
        e = WebDriverWait(self.browser, 10).until(
             lambda driver: self.browser.find_element_by_id(uname_el_id))
        e.send_keys(uname)
        e = WebDriverWait(self.browser, 10).until(
             lambda driver: self.browser.find_element_by_id(pword_el_id))
        e.send_keys(pword)
        e = WebDriverWait(self.browser, 60).until(
             lambda driver:    self.browser.find_element_by_id(submit_el_id))
        e.click()

    #mostly exists as sanity on testing framework
    def testAjaxLoads(self):
        self.loadAjax()
        self.failUnless(self.browser.title == "ESP Scheduling Application")
        
    def testUpdateScheduledClass(self):
        self.loadAjax()

        #     #schedule a class on the server
        #     #self.loginAdmin()
        #     print "loaded ajax"
        #     self.loginAdmin()
        #     (section, rooms, times) = self.scheduleClass()
        #     print "scheduled a class"
        #     print section
        #     print rooms
        #     print times
         
        #     #self.browser.implicitly_wait(30)
        #     #section turns up in the browser after no more than 30 seconds
        #     el = self.browser.get_element_by_css('CLS_id_'+str(section.id))
        #     print el
        #     #self.failUnless()

