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

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.datatree.models import GetNode
from esp.program.models import Program, ClassSubject, ClassSection, ClassCategories
from esp.users.models import ESPUser
from random import Random
import string


def genProgramModuleTestCase(moduleClass):    
    class ProgramModuleTestCase(TestCase):
        def setUp(self):
            """ Create a Program to work with """
            super(self, ProgramModuleTestCase).setUp()

            self._max_prog_modules_id = ProgramModule.objects.order_by('-id')[0].id
            
            # We need all the Program Modules loaded up to do this properly
            from esp.program.modules.models import install as program_modules_install
            program_modules_install()

            self.module = moduleClass()
            self.programmodule = ProgramModule.objects.get(handler=self.module.module_properties_autopopulated()['handler'])

            self.prog_anchor = GetNode("Q/Programs/TestProgram/%s" % Random().sample(string.letters, 12))
            self.prog_urlname = "%s/%s" % (self.prog_anchor.parent.name, self.prog_anchor.name)
            self.prog = Program()

            # Create a random anchor, so that we can keep creating new programs
            self.prog.anchor = self.prog_anchor
            self.prog.grade_min = 8
            self.prog.grade_max = 11
            self.prog.director_email = "root@localhost"
            self.prog.class_size_min = 5
            self.prog.class_size_max = 30
            self.prog.program_size_max = 1000

            self.prog.program_modules.add(self.programmodule)

            self.prog.save()

            # Now, we need some class categories to play with
            self.class_categories = [ ClassCategories.objects.get_or_create(category='Academic', symbol='A')[0],
                                      ClassCategories.objects.get_or_create(category='Comedic', symbol='C')[0],
                                      ClassCategories.objects.get_or_create(category='Extracurricular', symbol='E')[0]
                                      ]

            # Stick some classes in this program
            self.classes = [ ClassSubject(), ClassSubject(), ClassSubject() ]
            for klass in self.classes:
                klass.anchor = self.prog_anchor
                klass.parent_program = self.prog
                klass.category = self.class_categories[0]
                klass.grade_min = 7
                klass.grade_max = 12
                klass.class_size_min = 0
                klass.class_size_max = 100
                klass.duration = 2
                klass.save()

                # And do the sketchtastic thing to get the DataTree node ID
                klass.anchor = GetNode("%s/Classes/%s" % (klass.anchor.get_uri(), klass.emailcode()))
                klass.anchor.friendly_name = "Sample Class"
                klass.anchor.save()
                klass.save()

                # And make a class section too, just for good measure.
                # After all, we're not much of a class if we don't have a section.
                section = ClassSection()
                section.anchor = GetNode("%s/Section1" % klass.anchor.get_uri())
                section.duration = 2
                section.parent_class = klass
                section.save()
                
            
            self.students = [ ESPUser(), ESPUser(), ESPUser(), ESPUser() ]
            for student in self.students:
                # Set up some students
                pass

            self.teachers = [ ESPUser(), ESPUser(), ESPUser() ]
            for teacher in self.teachers:
                # Set up some teachers
                pass
            
            
        def tearDown(self):
            """ Delete all the cruft that we just created """
            super(self, ProgramModuleTestCase).tearDown()

            for student in self.students:
                student.delete()

            for teacher in self.teachers:
                teacher.delete()

            for klass in self.classes:
                klass.sections.all().delete()
                klass.delete()
            
            self.prog.delete()
            ProgramModule.objects.filter(id__gt=self._max_prog_modules_id).delete()
            self.prog_anchor.delete()

            for category in self.class_categories:
                category.delete()

    return ProgramModuleTestCase
            
