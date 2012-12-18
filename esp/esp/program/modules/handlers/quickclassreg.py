
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

from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_any_deadline, main_call, aux_call
from esp.program.models  import ClassSubject
from esp.program.controllers.classreg import ClassCreationController
from esp.web.util        import render_to_response
from esp.users.models    import ESPUser
from esp.db.forms import AjaxForeignKeyNewformField
from django import forms

class QuickClassRegForm(forms.Form):
    class_title = forms.CharField()
    teacher = AjaxForeignKeyNewformField(key_type=ESPUser,
                                         field_name='teacher',
                                         label='Teacher')

class QuickClassReg(ProgramModuleObj):
    """
    Allows admins to quickly register classes. Intended for
    e.g. Junction and Delve.
    """

    @classmethod
    def module_properties(cls):
        return [{
            "admin_title": "Admin Quick Class Reg",
            "link_title": "Admin Quick Class Reg",
            "module_type": "manage",
            }]

    @main_call
    @needs_admin
    def quickclassreg(self, request, tl, one, two, module, extra, prog):
        status = None
        if request.method == 'POST':
            form = QuickClassRegForm(request.POST)
            if form.is_valid():
                class_title = form.cleaned_data['class_title']
                teacher = form.cleaned_data['teacher']
                self.makeclass(prog, class_title, teacher)
                status = 'success'
            else:
                status = 'error'
        else:
            form = QuickClassRegForm()

        context = {}
        context['form'] = form
        context['status'] = status

        return render_to_response(self.baseDir()+'quickclassreg.html',
                                  request, (prog, tl), context)

    def makeclass(self, prog, title, teacher):
        """
        Makes a class with the absolute minimum amount of information.
        Required fields are filled in with semi-arbitrary values.
        """

        cls = ClassSubject()
        ccc = ClassCreationController(prog)
        ccc.attach_class_to_program(cls)
        cls.category = prog.class_categories.all()[0]
        cls.grade_min = prog.grade_min
        cls.grade_max = prog.grade_max
        cls.duration = 0.0
        cls.save()
        ccc.update_class_anchorname(cls, title)
        ccc.associate_teacher_with_class(cls, teacher)
        cls.add_default_section()
        cls.accept()
        return cls

    class Meta:
        abstract = True

