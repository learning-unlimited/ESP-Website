__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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
  Email: web-team@learningu.org
"""

from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest

import random
import re

class ModuleExistenceTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):

        # Set up the program -- we want to be sure of these parameters
        kwargs.update( {
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 6, 'classes_per_teacher': 1, 'sections_per_class': 2,
            'num_rooms': 6,
            } )
        super(ModuleExistenceTest, self).setUp(*args, **kwargs)

        #   Make all modules non-required for now, so we don't have to be shown required pages
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

    def target_module_list(self, tl=None):
        prog_mods = filter(lambda x: x.isStep(), self.program.getModules(tl=tl))
        prog_mods.sort(key=lambda x: x.id)
        return prog_mods

    def observed_module_list(self, tl, page_content):
        prog_modules = self.program.getModules(tl=tl)
        modules_found = []

        #   Find normal links
        pat1 = r'<a href="(?P<linkurl>[a-zA-z0-9_/]+)" title="(?P<linktitle>.*?)" class="vModuleLink" >(.*?)</a>'
        re_links_normal = re.findall(pat1, page_content, re.DOTALL)
        link_titles = [x[1] for x in re_links_normal]

        #   Find inline template links
        pat2 = r'<a href="#module-(?P<moduleid>[0-9]+)" title="(?P<linktitle>.*?)">(.*?)</a>'
        re_links_inline = re.findall(pat2, page_content, re.DOTALL)
        inline_ids = [int(x[0]) for x in re_links_inline]

        for mod in prog_modules:
            if (mod.module.link_title in link_titles) or (mod.id in inline_ids):
                modules_found.append(mod)

        return modules_found

    def check_reg_modules(self, core_url, tl):
        """ Check that the modules linked from the requested core registration page
            are consistent with those associated with the program. """

        #   Fetch the registration page and the lists of desired/actual modules
        response = self.client.get('/%s/%s/%s' % (tl, self.program.getUrlBase(), core_url))
        self.assertEqual(response.status_code, 200)
        actual_modules = self.observed_module_list(tl, response.content)
        target_modules = self.target_module_list(tl)

        #   Compare the module lists.
        #   We have to check with IDs because getModules() casts each module
        #   into a different class, which confuses Django's __eq__() function.
        actual_module_ids = [x.id for x in actual_modules]
        target_module_ids = [x.id for x in target_modules]

        missing_mods = []
        extra_mods = []
        for i in range(len(target_modules)):
            if target_module_ids[i] not in actual_module_ids:
                missing_mods.append(target_modules[i])
        for i in range(len(actual_modules)):
            if actual_module_ids[i] not in target_module_ids:
                missing_mods.append(actual_modules[i])

        #   Report any inconsistencies we detected.
        self.assertTrue(len(missing_mods) == 0, 'Missing modules: %s' % [x.__class__.__name__ for x in missing_mods])
        self.assertTrue(len(extra_mods) == 0, 'Extra modules: %s' % [x.__class__.__name__ for x in extra_mods])

    def test_studentreg(self):
        """ Ensure that the list of modules on the student reg page is correct """

        #   Pick a student and log on
        student = random.choice(self.students)
        self.assertTrue( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )

        #   Get student reg page and check list of modules
        self.check_reg_modules('studentreg', 'learn')

        #   Remove a module and check list is still consistent
        possible_modules = [x.module.id for x in self.target_module_list('learn')]
        module_to_remove = random.choice(possible_modules)
        self.program.program_modules.remove(module_to_remove)
        self.check_reg_modules('studentreg', 'learn')

        #   Restore it and re-check
        self.program.program_modules.add(module_to_remove)
        self.check_reg_modules('studentreg', 'learn')

    def test_teacherreg(self):
        """ Ensure that the list of modules on the teacher reg page is correct """

        #   Pick a teacher and log on
        teacher = random.choice(self.teachers)
        self.assertTrue( self.client.login( username=teacher.username, password='password' ), "Couldn't log in as teacher %s" % teacher.username )

        #   Get teacher reg page and check list of modules
        self.check_reg_modules('teacherreg', 'teach')

        #   Remove a module and check list is still consistent
        possible_modules = [x.module.id for x in self.target_module_list('teach')]
        module_to_remove = random.choice(possible_modules)
        self.program.program_modules.remove(module_to_remove)
        self.check_reg_modules('teacherreg', 'teach')

        #   Restore it and re-check
        self.program.program_modules.add(module_to_remove)
        self.check_reg_modules('teacherreg', 'teach')
