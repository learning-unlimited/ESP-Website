
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.program.manipulators import SATPrepInfoManipulator
from django import forms
from django.core.cache import cache
from esp.program.models import SATPrepRegInfo
from esp.users.models   import ESPUser, User
from esp.db.models      import Q, QNot
from django.template.defaultfilters import urlencode
from django.template import Context, Template
from esp.miniblog.models import Entry


class CommModule(ProgramModuleObj):
    """ Want to email all ESP students within a 60 mile radius of NYC?
    How about emailing all esp users within a 30 mile radius of New Hampshire whose last name contains 'e' and 'a'?
    Do that and even more useful things in the communication panel.
    """


    def students(self,QObject = False):
        if QObject:
            return {'satprepinfo': Q(satprepreginfo__program = self.program)}
        students = ESPUser.objects.filter(satprepreginfo__program = self.program).distinct()
        return {'satprepinfo': students }

    def isCompleted(self):
        
	satPrep = SATPrepRegInfo.getLastForProgram(self.user, self.program)
	return satPrep.id is not None

    @needs_admin
    def commfinal(self, request, tl, one, two, module, extra, prog):
        from esp.dbmail.models import MessageRequest
        from esp.users.models import PersistentQueryFilter
        
        announcements = self.program.anchor.tree_create(['Announcements'])
        filterid, subject, body  = [request.POST['filterid'],
                                    request.POST['subject'],
                                    request.POST['body']    ]


        if request.POST.has_key('from') and \
           len(request.POST['from'].strip()) > 0:
            fromemail = request.POST['from']
        else:
            fromemail = None

        filterobj = PersistentQueryFilter.getFilterFromID(filterid, User)

        variable_modules = {'user': self.user, 'program': self.program}

        newmsg_request = MessageRequest.createRequest(var_dict   = variable_modules,
                                                      subject    = subject,
                                                      recipients = filterobj,
                                                      sender     = fromemail,
                                                      creator    = self.user,
                                                      msgtext    = body)

        newmsg_request.save()

        foo = MessageRequest.objects.all()[0]

        # now we're going to process everything
        # nah, we'll do this later.
        #newmsg_request.process()

        numusers = filterobj.getList(User).count()

        from django.conf import settings
        if hasattr(settings, 'EMAILTIMEOUT') and \
               settings.EMAILTIMEOUT is not None:
            est_time = settings.EMAILTIMEOUT * len(users)
        else:
            est_time = 1.5 * numusers
            

        #        assert False, self.baseDir()+'finished.html'
        return render_to_response(self.baseDir()+'finished.html', request,
                                  (prog, tl), {'time': est_time})



    @needs_admin
    def commstep2(self, request, tl, one, two, module, extra, prog):
        pass
        

    @needs_admin
    def maincomm(self, request, tl, one, two, module, extra, prog):
        from esp.users.views     import get_user_list
        filterObj, found = get_user_list(request, self.program.getLists(True))

        if not found:
            return filterObj

        listcount = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()

        return render_to_response(self.baseDir()+'step2.html', request,
                                  (prog, tl), {'listcount': listcount,
                                               'filterid' : filterObj.id})

        #getFilterFromID(id, model)

    @needs_student
    def satprepinfo(self, request, tl, one, two, module, extra, prog):
	manipulator = SATPrepInfoManipulator()
	new_data = {}
	if request.method == 'POST':
		new_data = request.POST.copy()
		
		errors = manipulator.get_validation_errors(new_data)
		
		if not errors:
			manipulator.do_html2python(new_data)
			new_reginfo = SATPrepRegInfo.getLastForProgram(request.user, prog)
			new_reginfo.addOrUpdate(new_data, request.user, prog)

                        return self.goToCore(tl)
	else:
		satPrep = SATPrepRegInfo.getLastForProgram(request.user, prog)
		
		new_data = satPrep.updateForm(new_data)
		errors = {}

	form = forms.FormWrapper(manipulator, new_data, errors)
	return render_to_response('program/modules/satprep_stureg.html', request, (prog, tl), {'form':form})


