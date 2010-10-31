
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
  Email: web-team@lists.learningu.org
"""
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.program.models import ClassSubject, Program
from esp.users.models import UserBit, ESPUser

class AdminMaterials(ProgramModuleObj):
    doc = """ This allows you to view the submitted documents for all classes
    on one page. You can also upload documents particular to the program,
    such as liability waivers and information sheets.
    """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Course Materials",
            "link_title": "Manage Documents",
            "module_type": "manage",
            "seq": -9999
            }

    @main_call
    @needs_admin
    def get_materials(self, request, tl, one, two, module, extra, prog):
        from esp.web.forms.fileupload_form import FileUploadForm_Admin    
        from esp.qsdmedia.models import Media
        from esp.datatree.models import DataTree, GetNode, QTree, get_lowest_parent, StringToPerm, PermToString            
        context_form = FileUploadForm_Admin()
        new_choices = [(a.anchor.id, a.emailcode() + ': ' + unicode(a)) for a in prog.classes()]
        new_choices.append((prog.anchor.id,'Document pertains to program'))
        new_choices.reverse()
        context_form.set_choices(new_choices)
    
        if request.method == 'POST':
            if request.POST['command'] == 'delete':
                docid = request.POST['docid']
                media = Media.objects.get(id = docid)
                media.delete()
            	
            elif request.POST['command'] == 'add':
                form = FileUploadForm_Admin(request.POST, request.FILES)
                form.set_choices(new_choices)
                
                if form.is_valid():
                    ufile = form.cleaned_data['uploadedfile']
                    #	Append the class code on the filename if necessary
                    target_id = int(form.cleaned_data['target_obj'])
                    if target_id != prog.anchor.id:
                        desired_filename = ClassSubject.objects.get(anchor__id = target_id).emailcode() + '_' + ufile.name
                    else:
                        desired_filename = ufile.name

                    media = Media(friendly_name=form.cleaned_data['title'], anchor=DataTree.objects.get(id = form.cleaned_data['target_obj']))
                    media.handle_file(ufile, desired_filename)
                    
                    media.format = ''
                    media.save()
                else:
                    context_form = form

        context = {'prog': self.program, 'module': self, 'uploadform': context_form}
        
        classes = ClassSubject.objects.filter(parent_program = prog)
    
        return render_to_response(self.baseDir()+'listmaterials.html', request, (prog, tl), context)
    


