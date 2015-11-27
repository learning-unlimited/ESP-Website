from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.tests.ajaxschedulingmodule import AJAXSchedulingModuleTestBase

from django.test import LiveServerTestCase

from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
import time

class AJAXSchedulingModuleUITest(AJAXSchedulingModuleTestBase, LiveServerTestCase):
    def setUp(self, *args, **kwargs):
         super(AJAXSchedulingModuleUITest, self).setUp(*args, **kwargs)
         self.browser = WebDriver()
         self.update_interval = 4
         self.filter_interval = 5

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

    def isScheduled(self, section_id):
        elements = self.browser.find_elements_by_class_name('CLS_id_'+str(section_id))
        for el in elements:
            self.failIf(self.hasCSSClass(el, "class-entry"), "Scheduled class appears in directory")

        self.failUnless(True in [self.hasCSSClass(el, "matrix-cell") for el in elements],
            "Scheduled class does not appear in matrix")

    def isInDirectory(self, section_id):
        elements = self.browser.find_elements_by_class_name('CLS_id_'+str(section_id))
        self.failUnless(True in [self.hasCSSClass(el, "class-entry") for el in elements],
                        "Class does not appear in directory.")

    def isNotInDirectory(self, section_id):
        elements = self.browser.find_elements_by_class_name('CLS_id_'+str(section_id))
        for el in elements:
            self.failIf(self.hasCSSClass(el, "class-entry"), "Class appears in directory")

    def isNotScheduled(self, section_id):
        elements = self.browser.find_elements_by_class_name('CLS_id_'+str(section_id))
        for el in elements:
            self.failIf(self.hasCSSClass(el, "matrix-cell"), "Unscheduled class appears in matrix")

        self.failUnless(True in [self.hasCSSClass(el, "class-entry") for el in elements],
                        "Unscheduled class does not appear in directory.")

    #mostly exists as sanity on testing framework
    def testAjaxLoads(self):
        self.loadAjax()
        self.failUnless(self.browser.title == "ESP Scheduling Application", "Did not find AJAX: " + self.browser.title)

    def testUpdateScheduledClass(self):
        self.loadAjax()
        self.clearScheduleAvailability()
        (section, rooms, times) = self.scheduleClass()

        #section turns up in the browser
        time.sleep(self.update_interval)
        self.isScheduled(section.id)

    def testUpdateUnscheduledClass(self):
        self.loadAjax()
        self.clearScheduleAvailability()

        #schedule and unschedule a class
        (section, rooms, times) = self.scheduleClass()
        #wait for class to appear
        time.sleep(self.update_interval)
        self.unschedule_class(section.id)
        time.sleep(self.update_interval)

        self.isNotScheduled(section.id)

    def testUpdateScheduleUnscheduleClass(self):
        #if a class is scheduled and unscheduled in the same log, make sure it doesn't show up
        self.loadAjax()
        self.clearScheduleAvailability()

        #schedule and unschedule a class
        (section, rooms, times) = self.scheduleClass()
        self.unschedule_class(section.id)
        time.sleep(self.update_interval)

        self.isNotScheduled(section.id)

    # test basic drag-and-drop scheduling
    # this test does not seem to work correctly
    #
    # def testScheduleClass(self):
    #     self.loadAjax()
    #     self.clearScheduleAvailability()

    #     (section, room, times) = self.getClassToSchedule()
    #     source_el = self.browser.find_element_by_class_name('CLS_id_'+str(section.id))
    #     #any matrix cell will work
    #     target_el = self.browser.find_element_by_class_name('matrix-cell')

    #     ac = ActionChains(self.browser)
    #     ac.drag_and_drop(source_el, target_el).perform()
    #     time.sleep(5)
    #     self.isScheduled(section.id)

    #####################################################################################
    #
    #   FILTERING TESTS
    #
    #####################################################################################

    def filter_directory(self, label, value):
        #   Expand the filtering accordiion
        self.browser.find_element_by_id("filtering_header").click()
        time.sleep(1.0)
        #   Type into the desired filtering element
        f = self.browser.find_element_by_id("filter_"+label)
        f.send_keys(value + "\n")
        time.sleep(self.filter_interval)

    def testTitleFilter(self):
        self.loadAjax()

        section = self.program.sections()[0]

        self.filter_directory("Title", section.title())

        for s in self.program.sections():
            if(s == section):
                self.isInDirectory(s.id)
            else:
                self.isNotInDirectory(s.id)

    #TODO:  none of the classes have teachers with names
    def testTeacherFilter(self):
        self.loadAjax()
        self.clearScheduleAvailability()

        teacher = self.teachers[0]

        self.filter_directory("Teacher", teacher.name())

        for s in self.program.sections():
            if teacher in s.teachers:
                self.isInDirectory(s.id)
            else:
                self.isNotInDirectory(s.id)

    def testFilterUnscheduledClass(self):
        self.loadAjax()
        self.clearScheduleAvailability()

        (section, rooms, times) = self.scheduleClass()
        self.browser.find_element_by_id("filtering_header").click()
        title_filter = self.browser.find_element_by_id("filter_ID")
        title_filter.send_keys("xuoeahtuoeathsnuoeathns\n")#something I'm pretty sure won't appear in an id
        time.sleep(self.update_interval)

        self.unschedule_class(section.id)
        time.sleep(self.update_interval)

        self.isNotInDirectory(section.id)

    #TODO:  change some class length so we see it not filtering some stuff
    def testLengthFilter(self):
        self.loadAjax()
        self.clearScheduleAvailability()

        self.filter_directory("Min-length", "1")
        self.filter_directory("Max-length", "1")

        for s in self.program.sections():
            #all classes have length 2 in test data
            self.isNotInDirectory(s.id)

    #TODO:  status filter
    #TODO:  max size filter
