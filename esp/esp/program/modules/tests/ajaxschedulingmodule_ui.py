from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.tests.ajaxschedulingmodule import AJAXSchedulingModuleTestBase
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
import time

class AJAXSchedulingModuleUITest(AJAXSchedulingModuleTestBase):
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

    def loadAjax(self):
        self.loginAdminBrowser(self.admins[0].username, "password")
        url = self.live_server_url + self.ajax_url_base + "ajax_scheduling"
        self.browser.get(url)
        #wait for ajax to load before we go on
        time.sleep(30)

    def hasCSSClass(self, el, class_name):
        css_classes = el.get_attribute("class").split()
        return class_name in css_classes

    #mostly exists as sanity on testing framework
    def testAjaxLoads(self):
        self.loadAjax()
        self.failUnless(self.browser.title == "ESP Scheduling Application", "Did not find AJAX: " + self.browser.title)
        
    def testUpdateScheduledClass(self):
        self.loadAjax()
        self.clearScheduleAvailability()
        (section, rooms, times) = self.scheduleClass()         

        #section turns up in the browser after no more than 30 seconds
        time.sleep(30)
        elements = self.browser.find_elements_by_class_name('CLS_id_'+str(section.id))
        for el in elements:
            self.failIf(self.hasCSSClass(el, "class-entry"), "Scheduled class appears in directory")

        self.failUnless(True in [self.hasCSSClass(el, "matrix-cell") for el in elements],
            "Scheduled class does not appear in matrix")

    def testUpdateUnscheduledClass(self):
        self.loadAjax()
        self.clearScheduleAvailability()

        #schedule and unschedule a class
        (section, rooms, times) = self.scheduleClass()         
        self.unschedule_class(section.id)
        
        #wait for changelog
        time.sleep(30)
    
        #assert that the class is in the directory
        elements = self.browser.find_elements_by_class_name('CLS_id_'+str(section.id))
        print len(elements)
        for el in elements:
            self.failIf(self.hasCSSClass(el, "matrix-cell"), "Unscheduled class appears in matrix")
            
        self.failUnless(True in [self.hasCSSClass(el, "class-entry") for el in elements], 
                        "Unscheduled class does not appear in directory.")

    def testScheduleClass(self):
        self.loadAjax()
        self.clearScheduleAvailability()

        #section = 

        ac = ActionChains(driver)
        source = self.browser.find_element_by_class_name('CLS_id_'+str(section.id))
