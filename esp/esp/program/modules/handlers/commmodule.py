
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
from esp.program.modules.base import ProgramModuleObj, needs_student, needs_admin, main_call, aux_call
from esp.web.util        import render_to_response
from esp.program.modules.forms.satprep import SATPrepInfoForm
from esp.program.models import SATPrepRegInfo
from esp.users.models   import ESPUser, User
from django.db.models.query   import Q
from esp.dbmail.models import ActionHandler
from django.template import Template
from esp.middleware.threadlocalrequest import AutoRequestContext as Context
from esp.middleware import ESPError

class CommModule(ProgramModuleObj):
    """ Want to email all ESP students within a 60 mile radius of NYC?
    How about emailing all esp users within a 30 mile radius of New Hampshire whose last name contains 'e' and 'a'?
    Do that and even more useful things in the communication panel.
    """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Communications Panel for Admin",
            "link_title": "Communications Panel",
            "module_type": "manage",
            "seq": 10
            }
    
    def students(self,QObject = False):
        if QObject:
            return {'satprepinfo': Q(satprepreginfo__program = self.program)}
        students = User.objects.filter(satprepreginfo__program = self.program).distinct()
        return {'satprepinfo': students }

    def isCompleted(self):
        
        satPrep = SATPrepRegInfo.getLastForProgram(self.user, self.program)
        return satPrep.id is not None

    @aux_call
    @needs_admin
    def commprev(self, request, tl, one, two, module, extra, prog):
        from esp.users.models import PersistentQueryFilter
        from django.conf import settings

        filterid, listcount, subject, body = [request.POST['filterid'],
                                              request.POST['listcount'],
                                              request.POST['subject'],
                                              request.POST['body']    ]

        # Set From address
        if request.POST.has_key('from') and \
           len(request.POST['from'].strip()) > 0:
            fromemail = request.POST['from']
        else:
            # String together an address like username@esp.mit.edu
            fromemail = '%s@%s' % (self.user.username, settings.SITE_INFO[1])
        
        # Set Reply-To address
        if request.POST.has_key('replyto') and len(request.POST['replyto'].strip()) > 0:
            replytoemail = request.POST['replyto']
        else:
            replytoemail = fromemail

        try:
            filterid = int(filterid)
        except:
            raise ESPError(), "Corrupted POST data!  Please contact us at esp-web@mit.edu and tell us how you got this error, and we'll look into it."

        userlist = PersistentQueryFilter.getFilterFromID(filterid, User).getList(User)

        try:
            firstuser = userlist[0]
        except:
            raise ESPError(), "You seem to be trying to email 0 people!  Please go back, edit your search, and try again."

        #   If they were trying to use HTML, don't sanitize the content.
        if '<html>' not in body:
            htmlbody = body.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br />')
        else:
            htmlbody = body
            
        esp_firstuser = ESPUser(firstuser)
        contextdict = {'user'   : ActionHandler(esp_firstuser, esp_firstuser),
                       'program': ActionHandler(self.program, esp_firstuser) }
        renderedtext = Template(htmlbody).render(Context(contextdict))
        renderedtext = renderedtext.replace('\n', '<br />')
        
        return render_to_response(self.baseDir()+'preview.html', request,
                                  (prog, tl), {'filterid': filterid,
                                               'listcount': listcount,
                                               'subject': subject,
                                               'from': fromemail,
                                               'replyto': replytoemail,
                                               'body': body,
                                               'renderedtext': renderedtext})


    @aux_call
    @needs_admin
    def commfinal(self, request, tl, one, two, module, extra, prog):
        from esp.dbmail.models import MessageRequest
        from esp.users.models import PersistentQueryFilter
        
        announcements = self.program_anchor_cached().tree_create(['Announcements'])
        filterid, fromemail, replytoemail, subject, body = [
                                    request.POST['filterid'],
                                    request.POST['from'],
                                    request.POST['replyto'],
                                    request.POST['subject'],
                                    request.POST['body']    ]
        
        try:
            filterid = int(filterid)
        except:
            raise ESPError(), "Corrupted POST data!  Please contact us at esp-web@mit.edu and tell us how you got this error, and we'll look into it."
        
        filterobj = PersistentQueryFilter.getFilterFromID(filterid, User)

        variable_modules = {'user': self.user, 'program': self.program}

        newmsg_request = MessageRequest.createRequest(var_dict   = variable_modules,
                                                      subject    = subject,
                                                      recipients = filterobj,
                                                      sender     = fromemail,
                                                      creator    = self.user,
                                                      msgtext    = body,
                                                      special_headers_dict
                                                                 = { 'Reply-To': replytoemail, }, )

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


    @aux_call
    @needs_admin
    def commstep2(self, request, tl, one, two, module, extra, prog):
        pass

    
    @main_call
    @needs_admin
    def maincomm(self, request, tl, one, two, module, extra, prog):
        from esp.users.views     import get_user_list
        filterObj, found = get_user_list(request, self.program.getLists(True))

        if not found:
            return filterObj

        listcount = User.objects.filter(filterObj.get_Q()).distinct().count()

        return render_to_response(self.baseDir()+'step2.html', request,
                                  (prog, tl), {'listcount': listcount,
                                               'filterid': filterObj.id })

        #getFilterFromID(id, model)

    @aux_call
    @needs_admin
    def maincomm2(self, request, tl, one, two, module, extra, prog):

        filterid, listcount, fromemail, replytoemail, subject, body = [
                                                         request.POST['filterid'],
                                                         request.POST['listcount'],
                                                         request.POST['from'],
                                                         request.POST['replyto'],
                                                         request.POST['subject'],
                                                         request.POST['body']    ]

        return render_to_response(self.baseDir()+'step2.html', request,
                                  (prog, tl), {'listcount': listcount,
                                               'filterid': filterid,
                                               'from': fromemail,
                                               'replyto': replytoemail,
                                               'subject': subject,
                                               'body': body})

    @needs_student
    def satprepinfo(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            form = SATPrepInfoForm(request.POST)

            if form.is_valid():
                reginfo = SATPrepRegInfo.getLastForProgram(request.user, prog)
                form.instance = reginfo
                form.save()

                return self.goToCore(tl)
        else:
            satPrep = SATPrepRegInfo.getLastForProgram(request.user, prog)
            form = SATPrepInfoForm(instance = satPrep)

        return render_to_response('program/modules/satprep_stureg.html', request, (prog, tl), {'form':form})


