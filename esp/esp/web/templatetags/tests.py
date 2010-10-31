
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""

__all__ = ['TexImagesTest']

from esp.tests.util import CacheFlushTestCase as TestCase
import re

from esp.web.templatetags.latex import teximages
from settings import MEDIA_URL

_imgre = re.compile('<img src="(%s[^"]*)"[^>]*alt="([^"]*)"[^>]*>' % MEDIA_URL)

class TexImagesTest(TestCase):
    """ Tests for the inline LaTeX template tag. """

    def setUp(self):
        pass
    def tearDown(self):
        pass

    def extractImages(self, string, expect = -1):
        """ Extracts image tags out of a string. """
        # this is kinda hacky...
        imglist = [ {'img' : m.group(0), 'url' : m.group(1), 'alt' : m.group(2)} for m in re.finditer(_imgre, string) ]
        if expect >= 0:
            self.failUnless(len(imglist) is expect,
                    "Found %d instead of the expected %d images in the string." % (len(imglist), expect))
        return imglist

    def testFilter(self):
        """ Tests filtering of a string. """
        string = r"Foo bar baz $$x+y+z$$. I like oranges. Aren't hippos $$tasty$$?"
        processed = teximages(string)
        imglist = self.extractImages(processed, 2)
        self.failUnlessEqual(imglist[0]['alt'], 'x+y+z', "Alt text 'x+y+z' expected. Got '%s'" % imglist[0]['alt'])
        self.failUnlessEqual(imglist[1]['alt'], 'tasty', "Alt text 'tasty' expected. Got '%s'" % imglist[1]['alt'])

    def testBadTex(self):
        """ Tests graceful handling of bad TeX code. """
        string = r"""My class will be on fractions. Aren't fractions $$\frac{\text{fun}}{\text{fun}}}$$?
                Here we will learn about $$\mangoes$$ and bad $$\LaTeX \that \annoys \esp \webmins$$.
                Yeah. Aren't I special?"""
        processed = teximages(string)
        imglist = self.extractImages(processed, 0)
        self.failUnlessEqual(string, processed, "String without (good) TeX should have been left unchanged.")

    def testDuplicate(self):
        """ Tests that an equation appearing twice points to the same image. """
        string = r"""My goal tonight was a simple one. To come up here and at no
        point seem like a condescending, egomaniacal bully, and I'm gonna be
        honest, I think I nailed it. Sure there were moments when I wanted to
        say, 'Hey, this lady is a dummy!' But I didn't. Because $$\emph{Joe Biden is better than that}$$.
        I repeat $$\emph{Joe Biden is better than that}$$.
        So to all of the pundits who said I would seem cocky or
        arrogant. You dopes got schooled Biden-style."""
        processed = teximages(string)
        imglist = self.extractImages(processed, 2)
        self.failUnlessEqual(imglist[0], imglist[1], "Identical snippets did not return identical images")

    def testDefaultDPI(self):
        """ Tests that the DPI defaults to 150. """
        string = r"Foo bar baz $$x+y+z$$. I like oranges. Aren't hippos $$tasty$$?"
        processed1 = teximages(string)
        processed2 = teximages(string, dpi=150)
        # Verify images were created
        self.extractImages(processed1, 2)
        self.extractImages(processed2, 2)
        self.failUnlessEqual(processed1, processed2, "Default DPI did not produce the same output as size 150.")

    def testDistinctDPI(self):
        """ Tests that different DPIs result in different image links. """
        string = r"Foo bar baz $$x+y+z$$. I like oranges. Aren't hippos $$tasty$$?"
        processed1 = teximages(string, dpi=500)
        processed2 = teximages(string, dpi=150)
        # Verify images were created
        self.extractImages(processed1, 2)
        self.extractImages(processed2, 2)
        self.failIfEqual(processed1, processed2, "Different DPIs produced the same text.")
