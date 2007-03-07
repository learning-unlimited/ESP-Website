
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""


class TestCase(object):
    """ Yay, it's a hacked minimal implementation of TestCase! """
    def runTest(self):
        print "no Run"
    def setUp(self):
        print "no setUp"
    def tearDown(self):
        print "no tearDown"


class TestSuite(object):
    testList = []
    def __init__(self, arg=[]):
        self.addTest(arg)
    def addTest(self, test):
        self.testList.append(test)


class TextTestRunner(object):
    def run(self, tests):
        print "Running Test: " + str(tests)
        if type(tests) == type([]):
            print "Branching on a list"
            for t in tests:
                if t != tests:
                    self.run(t)
        elif type(tests) == type(TestSuite()):
            print "Branching"
            for t in tests.testList:
                if t != tests.testList:
                    self.run(t)
        else:
            print "Running!"
            t = tests()
            print str(tests)
            print str(t)
            
            try:
                t.setUp()
            except:
                print "Error in setUp: " + str(t.__doc__)
                raise
            
            try:
                t.runTest()
            except:
                print "Error in runTest: " + str(t.__doc__)
                raise

            try:
                t.tearDown()
            except:
                print "Error in tearDown: " + str(t.__doc__)
                raise

            print str(t.__doc__) + " successful!"

