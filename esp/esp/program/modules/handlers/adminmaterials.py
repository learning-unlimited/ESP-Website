
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
            "link_title": "Manage Documents",
            "module_type": "manage",
            "seq": -9999
            }

    @main_call
    @needs_admin
    def get_materials(self, request, tl, one, two, module, extra, prog):
        from esp.web.forms.fileupload_form import FileUploadForm_Admin    
        from esp.qsdmedia.models import Media
	from esp.datatree.models import DataTree
	    
	context_form = FileUploadForm_Admin()
	new_choices = [(a.anchor.id, a.emailcode() + ': ' + str(a)) for a in prog.classes()]
	new_choices.append((prog.anchor.id,'Document pertains to program'))
	new_choices.reverse()
	context_form.set_choices(new_choices)
	
        if request.method == 'POST':
            if request.POST['command'] == 'delete':
                docid = request.POST['docid']
                media = Media.objects.get(id = docid)
                media.delete()
            	
            elif request.POST['command'] == 'add':
                data = request.POST.copy()
                data.update(request.FILES)
                form = FileUploadForm_Admin(data)
                form.set_choices(new_choices)
                
                if form.is_valid():
                    media = Media(friendly_name = form.clean_data['title'], anchor = DataTree.objects.get(id = form.clean_data['target_obj']))
	            
		    #	Append the class code on the filename if necessary
		    target_id = int(form.clean_data['target_obj'])
	            if target_id != prog.anchor.id:
                        new_target_filename = ClassSubject.objects.get(anchor__id = target_id).emailcode() + '_' + form.clean_data['uploadedfile']['filename']
                    else:
                        new_target_filename =  form.clean_data['uploadedfile']['filename']

                    media.save_target_file_file(new_target_filename, form.clean_data['uploadedfile']['content'])
                    media.mime_type = form.clean_data['uploadedfile']['content-type']
	            media.size = len(form.clean_data['uploadedfile']['content'])
	            extension_list = form.clean_data['uploadedfile']['filename'].split('.')
	            extension_list.reverse()
	            media.file_extension = extension_list[0]
	            media.format = ''
		    
                    media.save()
	        else:
	            context_form = form

        context = {'prog': self.program, 'module': self, 'uploadform': context_form}
	
	classes = ClassSubject.objects.filter(parent_program = prog)
	
        return render_to_response(self.baseDir()+'listmaterials.html', request, (prog, tl), context)
    
 

