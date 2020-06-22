
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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
from django.http                 import Http404
from esp.program.modules.base    import ProgramModuleObj, main_call, aux_call, needs_account, needs_teacher
from esp.middleware              import ESPError
from esp.program.models          import ClassSubject, ClassSection
from datetime                    import timedelta
from esp.users.models            import ESPUser
from esp.middleware.threadlocalrequest import get_current_request
from esp.utils.web               import render_to_response

class TeacherPreviewModule(ProgramModuleObj):
    """ This program module allows teachers to view classes already added to the program.
        And, for now, also some printables. """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Teacher Class Previewing",
            "link_title": "Preview Other Classes",
            "module_type": "teach",
            "inline_template": "preview.html",
            "seq": -10,
            "choosable": 1,
            }

    def teacherhandout(self, request, tl, one, two, module, extra, prog, template_file='teacherschedules.html'):
        #   Use the template defined in ProgramPrintables
        from esp.program.modules.handlers import ProgramPrintables
        context = {'module': self}
        pmos = ProgramModuleObj.objects.filter(program=prog,module__handler__icontains='printables')
        if pmos.count() == 1:
            pmo = ProgramPrintables(pmos[0])
            if request.user.isAdmin() and 'user' in request.GET:
                teacher = ESPUser.objects.get(id=request.GET['user'])
            else:
                teacher = request.user
            scheditems = []
            for cls in teacher.getTaughtClasses().filter(parent_program = self.program):
                if cls.isAccepted():
                    for section in cls.sections.all():
                        scheditems.append({'name': teacher.name(), 'teacher': teacher, 'cls': section})
            scheditems.sort()
            context['scheditems'] = scheditems
            return render_to_response(pmo.baseDir()+template_file, request, context)
        else:
            raise ESPError('No printables module resolved, so this document cannot be generated.  Consult the webmasters.', log=False)

    @aux_call
    # No need for needs_teacher, since it depends on request.user, and onsite may want to use it (with ?user=foo).
    @needs_account
    def teacherschedule(self, request, tl, one, two, module, extra, prog):
        return self.teacherhandout(request, tl, one, two, module, extra, prog, template_file='teacherschedule.html')

    @aux_call
    # No need for needs_teacher, since it depends on request.user, and onsite may want to use it (with ?user=foo).
    @needs_account
    def classroster(self, request, tl, one, two, module, extra, prog):
        return self.teacherhandout(request, tl, one, two, module, extra, prog, template_file='classrosters.html')

    @aux_call
    @needs_teacher
    def catalogpreview(self, request, tl, one, two, module, extra, prog):
        try:
            qs = ClassSubject.objects.filter(id=int(extra))
            cls = qs[0]
        except (ValueError, IndexError):
            raise Http404('The requested class could not be found.')
        cls = ClassSubject.objects.catalog(cls.parent_program, force_all=True, initial_queryset=qs)[0]
        return render_to_response(self.baseDir()+'catalogpreview.html', request, {'class': cls})

    def get_handouts(self):
        sections = get_current_request().user.getTaughtSections(self.program)
        sections = filter(lambda x: x.isAccepted() and x.meeting_times.count() > 0, sections)
        if len(sections) > 0:
            return {'teacherschedule': 'Your Class Schedule', 'classroster': 'Class Rosters'}
        else:
            return {}

    def prepare(self, context={}):
        if context is None: context = {}

        classes = ClassSubject.objects.catalog(self.program, None, True)

        #   First, the already-registered classes.
        categories = {}
        for cls in classes:
            if cls.category_id not in categories:
                categories[cls.category_id] = {'id': cls.category_id, 'category': cls.category_txt if hasattr(cls, 'category_txt') else cls.category.category, 'classes': [cls]}
            else:
                categories[cls.category_id]['classes'].append(cls)

        context['categories'] = [categories[cat_id] for cat_id in categories]
        context['prog'] = self.program

        #   Then, the printables.
        handout_dict = self.get_handouts()
        context['handouts'] = [{'url': key, 'title': handout_dict[key]} for key in handout_dict]

        return context

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
