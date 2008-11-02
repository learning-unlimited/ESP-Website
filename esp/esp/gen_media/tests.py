
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 MIT ESP

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

import unittest
import os

__all__ = ['InlineLatexTest']

class InlineLatexTest(unittest.TestCase):
    """ Tests for the inline LaTeX system. """

    from esp.gen_media.inlinelatex import InlineLatex
    def setUp(self):
        self._to_kill = []

    def tearDown(self):
        # Clean up
        for img in self._to_kill:
            if os.path.exists(img.local_path()):
                os.remove(img.local_path())
        self._to_kill = []

    @staticmethod
    def getRandomEquation():
        """ Get a random equation --- we want new equations to test. """
        from random import randint
        return r"xy^{%d} + \frac{%d + 5x}{\sqrt{e^{%d z}}}" \
                % (randint(1, 50000), randint(1, 50000), randint(1, 50000))

    def getAndCheck(self, eqn, *args, **kwargs):
        """ Constructs and image and checks its validity - test fails otherwise. """
        img = InlineLatex(eqn, *args, **kwargs)

        self._to_kill.append(img) # Clean up later

        self.failIf(img.url() is None, "No URL was returned for %s." % eqn)
        local_path = img.local_path()
        self.failIf(local_path is None, "No local path was returned for %s." % eqn)
        self.failIf(img.img() is None, "No image tag was returned for %s." % eqn)
        self.failUnless(os.path.exists(local_path), "File %s does not exist for %s." % (local_path, eqn))

        return img
        
    def testGen(self):
        """ Test that an image was successfully generated. """
        eqn = self.getRandomEquation()
        img = self.getAndCheck(eqn)

    def testConsistent(self):
        """ Test that the same data gives the same path. """
        eqn = self.getRandomEquation()
        img1 = self.getAndCheck(eqn)
        img2 = self.getAndCheck(eqn)
        self.failUnlessEqual(img1.local_path(), img2.local_path(), "Returned paths inconsistent for %s." % eqn)

    def testDefaultDPI(self):
        """ Test that the default DPI is indeed 150. """
        eqn = self.getRandomEquation()
        img1 = self.getAndCheck(eqn)
        img2 = self.getAndCheck(eqn, dpi=150)
        self.failUnlessEqual(img1.local_path(), img2.local_path(), "Default DPI not 150.")

    def testDistinctDPI(self):
        """ Test that switching DPIs gives different images. """
        eqn = self.getRandomEquation()
        img1 = self.getAndCheck(eqn, dpi=200)
        img2 = self.getAndCheck(eqn, dpi=150)
        self.failIfEqual(img1.local_path(), img2.local_path(), "Images with different DPI saved at the same location.")

    def testDefaultStyle(self):
        """ Test that DISPLAY is the default style. """
        eqn = self.getRandomEquation()
        img1 = self.getAndCheck(eqn)
        img2 = self.getAndCheck(eqn, style='DISPLAY')
        self.failUnlessEqual(img1.local_path(), img2.local_path(), "Default style inconsistent.")

    def testDistinctStyle(self):
        """ Test that INLINE and DISPLAY give different images. """
        eqn = self.getRandomEquation()
        img1 = self.getAndCheck(eqn, style='INLINE')
        img2 = self.getAndCheck(eqn, style='DISPLAY')
        self.failIfEqual(img1.local_path(), img2.local_path(), "Images with different style saved at the same location.")

    def testBadInput(self):
        """ Test that invalid LaTeX throws an exception. """
        eqn = r"\frac{1}{\sqrt{5}"
        self.failUnlessRaises(ESPError, InlineLatex(eqn), "Exception not thrown when given invalid TeX expression.")
        self.failUnlessRaises(ESPError, InlineLatex(eqn, dpi=500), "Exception not thrown when given invalid TeX expression.")
        self.failUnlessRaises(ESPError, InlineLatex(eqn, dpi=500, style='INLINE'), "Exception not thrown when given invalid TeX expression.")
        self.failUnlessRaises(ESPError, InlineLatex(eqn, style='INLINE'), "Exception not thrown when given invalid TeX expression.")

    def testInvalidStyle(self):
        """ Test that an exception is thrown on invalid style. """
        self.failUnlessRaises(ESPError, InlineLatex(getRandomEquation(), style='ORANGES'), "Exception not thrown when given invalid style.")
        self.failUnlessRaises(ESPError, InlineLatex(getRandomEquation(), style='ORANGES'), "Exception not thrown when given invalid style.")
