
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
from esp.program.modules.base    import ProgramModuleObj
from esp.program.models          import Class
from datetime                    import timedelta

class TeacherPreviewModule(ProgramModuleObj):
    """ This program module allows teachers to view classes already added to the program. """

    def prepare(self, context={}):
        if context is None: context = {}

        classes = Class.objects.catalog(self.program, None, True)
        
        categories = {}
        for cls in classes:
            if cls.category_id not in categories:
                categories[cls.category_id] = {'id': cls.category_id, 'category': cls.category_txt, 'classes': [cls]}
            else:
                categories[cls.category_id]['classes'].append(cls)
        
        context['categories'] = [categories[cat_id] for cat_id in categories]
        
        return context
