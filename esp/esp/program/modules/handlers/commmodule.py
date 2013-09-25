
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
from esp.program.modules.base import ProgramModuleObj, needs_student, needs_admin, main_call, aux_call
from esp.web.util        import render_to_response
from esp.dbmail.models import MessageRequest
from esp.users.models   import ESPUser, PersistentQueryFilter
from esp.users.controllers.usersearch import UserSearchController
from esp.users.views.usersearch import get_user_checklist
from django.db.models.query   import Q
from esp.dbmail.models import ActionHandler
from django.template import Template
from django.template import Context as DjangoContext
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
            fromemail = '%s@%s' % (request.user.username, settings.SITE_INFO[1])
        
        # Set Reply-To address
        if request.POST.has_key('replyto') and len(request.POST['replyto'].strip()) > 0:
            replytoemail = request.POST['replyto']
        else:
            replytoemail = fromemail

        try:
            filterid = int(filterid)
        except:
            raise ESPError(), "Corrupted POST data!  Please contact us at esp-web@mit.edu and tell us how you got this error, and we'll look into it."

        userlist = PersistentQueryFilter.getFilterFromID(filterid, ESPUser).getList(ESPUser)

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
        renderedtext = Template(htmlbody).render(DjangoContext(contextdict))
        
        return render_to_response(self.baseDir()+'preview.html', request,
                                              {'filterid': filterid,
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
        
        filterobj = PersistentQueryFilter.getFilterFromID(filterid, ESPUser)

        variable_modules = {'user': request.user, 'program': self.program}

        newmsg_request = MessageRequest.createRequest(var_dict   = variable_modules,
                                                      subject    = subject,
                                                      recipients = filterobj,
                                                      sender     = fromemail,
                                                      creator    = request.user,
                                                      msgtext    = body,
                                                      special_headers_dict
                                                                 = { 'Reply-To': replytoemail, }, )

        newmsg_request.save()

        # now we're going to process everything
        # nah, we'll do this later.
        #newmsg_request.process()

        numusers = filterobj.getList(ESPUser).distinct().count()

        from django.conf import settings
        if hasattr(settings, 'EMAILTIMEOUT') and \
               settings.EMAILTIMEOUT is not None:
            est_time = settings.EMAILTIMEOUT * numusers
        else:
            est_time = 1.5 * numusers
            

        #        assert False, self.baseDir()+'finished.html'
        return render_to_response(self.baseDir()+'finished.html', request,
                                  {'time': est_time})


    @aux_call
    @needs_admin
    def commstep2(self, request, tl, one, two, module, extra, prog):
        pass

    
    @aux_call
    @needs_admin
    def commpanel_old(self, request, tl, one, two, module, extra, prog):
        from esp.users.views     import get_user_list
        filterObj, found = get_user_list(request, self.program.getLists(True))

        if not found:
            return filterObj

        listcount = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()

        return render_to_response(self.baseDir()+'step2.html', request,
                                              {'listcount': listcount,
                                               'filterid': filterObj.id })

    @main_call
    @needs_admin
    def commpanel(self, request, tl, one, two, module, extra, prog):
    
        usc = UserSearchController()
    
        context = {}

        #   If list information was submitted, continue to prepare a message
        if request.method == 'POST':
            #   Turn multi-valued QueryDict into standard dictionary
            data = {}
            for key in request.POST:
                data[key] = request.POST[key]
                
            ##  Handle normal list selecting submissions
            if ('base_list' in data and 'recipient_type' in data) or ('combo_base_list' in data):
        
                
                filterObj = usc.filter_from_postdata(prog, data)

                if data['use_checklist'] == '1':
                    (response, unused) = get_user_checklist(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, '/manage/%s/commpanel_old' % prog.getUrlBase())
                    return response
                    
                context['filterid'] = filterObj.id
                context['listcount'] = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()
                return render_to_response(self.baseDir()+'step2.html', request, context)
                
            ##  Prepare a message starting from an earlier request
            elif 'msgreq_id' in data:
                msgreq = MessageRequest.objects.get(id=data['msgreq_id'])
                context['filterid'] = msgreq.recipients.id
                context['listcount'] = msgreq.recipients.getList(ESPUser).count()
                context['from'] = msgreq.sender
                context['subject'] = msgreq.subject
                context['replyto'] = msgreq.special_headers_dict.get('Reply-To', '')
                context['body'] = msgreq.msgtext
                return render_to_response(self.baseDir()+'step2.html', request, context)
                
            else:
                raise ESPError(True), 'What do I do without knowing what kind of users to look for?'
        
        #   Otherwise, render a page that shows the list selection options
        context.update(usc.prepare_context(prog))
        
        return render_to_response(self.baseDir()+'commpanel_new.html', request, context)

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
                                              {'listcount': listcount,
                                               'filterid': filterid,
                                               'from': fromemail,
                                               'replyto': replytoemail,
                                               'subject': subject,
                                               'body': body})

    class Meta:
        abstract = True

