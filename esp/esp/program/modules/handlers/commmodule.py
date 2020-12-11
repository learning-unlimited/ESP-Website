
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
from esp.program.modules.base import ProgramModuleObj, needs_student, needs_admin, main_call, aux_call
from esp.program.modules.handlers.listgenmodule import ListGenModule
from esp.utils.web import render_to_response
from esp.dbmail.models import MessageRequest
from esp.users.models   import ESPUser, PersistentQueryFilter
from esp.users.controllers.usersearch import UserSearchController
from esp.users.forms.generic_search_form import StudentSearchForm
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
            "seq": 10,
            "choosable": 1,
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
        sendto_fn_name = request.POST.get('sendto_fn_name', MessageRequest.SEND_TO_SELF_REAL)
        selected = request.POST.get('selected')
        public_view = 'public_view' in request.POST

        # Set From address
        if request.POST.get('from', '').strip():
            fromemail = request.POST['from']
        else:
            # String together an address like username@esp.mit.edu
            fromemail = '%s@%s' % (request.user.username, settings.SITE_INFO[1])

        # Set Reply-To address
        if request.POST.get('replyto', '').strip():
            replytoemail = request.POST['replyto']
        else:
            replytoemail = fromemail

        try:
            filterid = int(filterid)
        except:
            raise ESPError("Corrupted POST data!  Please contact us at" +
            "websupport@learningu.org and tell us how you got this error," +
            "and we'll look into it.")

        userlist = PersistentQueryFilter.getFilterFromID(filterid, ESPUser).getList(ESPUser)

        try:
            firstuser = userlist[0]
        except:
            raise ESPError("You seem to be trying to email 0 people!  " +
            "Please go back, edit your search, and try again.")

        MessageRequest.assert_is_valid_sendto_fn_or_ESPError(sendto_fn_name)

        # If they used the rich-text editor, we'll need to add <html> tags
        if '<html>' not in body:
            body = '<html>' + body + '</html>'

        contextdict = {'user'   : ActionHandler(firstuser, firstuser),
                       'program': ActionHandler(self.program, firstuser) }

        renderedtext = Template(body).render(DjangoContext(contextdict))

        return render_to_response(self.baseDir()+'preview.html', request,
                                              {'filterid': filterid,
                                               'sendto_fn_name': sendto_fn_name,
                                               'listcount': listcount,
                                               'selected': selected,
                                               'subject': subject,
                                               'from': fromemail,
                                               'replyto': replytoemail,
                                               'public_view': public_view,
                                               'body': body,
                                               'renderedtext': renderedtext})

    @staticmethod
    def approx_num_of_recipients(filterObj, sendto_fn):
        """
        Approximates the number of recipients of a message, given the filter
        and the sendto function.
        """
        userlist = filterObj.getList(ESPUser).distinct()
        numusers = userlist.count()
        if numusers > 0:
            # Approximate the number of emails that each user will receive, by
            # taking the maximum number of emails per user over a small subset.
            # This is approximate because different users may receive different
            # numbers of emails, since the sendto functions remove duplicates.
            # And we don't attempt to get the exact number, because it doesn't
            # matter much and it would be expensive to evaluate the sendto
            # function for all users just to get that one number.
            emails_per_user = 1
            short_userlist = userlist[:min(numusers, 10)]
            for user in short_userlist:
                emails_per_user = max(emails_per_user, len(sendto_fn(user)))
            numusers *= emails_per_user
        return numusers


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
        sendto_fn_name = request.POST.get('sendto_fn_name', MessageRequest.SEND_TO_SELF_REAL)
        public_view = 'public_view' in request.POST

        try:
            filterid = int(filterid)
        except:
            raise ESPError("Corrupted POST data!  Please contact us at " +
            "websupport@learningu and tell us how you got this error, " +
            "and we'll look into it.")

        filterobj = PersistentQueryFilter.getFilterFromID(filterid, ESPUser)

        sendto_fn = MessageRequest.assert_is_valid_sendto_fn_or_ESPError(sendto_fn_name)

        variable_modules = {'user': request.user, 'program': self.program}

        newmsg_request = MessageRequest.createRequest(var_dict   = variable_modules,
                                                      subject    = subject,
                                                      recipients = filterobj,
                                                      sendto_fn_name  = sendto_fn_name,
                                                      sender     = fromemail,
                                                      creator    = request.user,
                                                      msgtext = body,
                                                      public = public_view,
                                                      special_headers_dict
                                                                 = { 'Reply-To': replytoemail, }, )

        newmsg_request.save()

        # now we're going to process everything
        # nah, we'll do this later.
        #newmsg_request.process()

        numusers = self.approx_num_of_recipients(filterobj, sendto_fn)

        from django.conf import settings
        if hasattr(settings, 'EMAILTIMEOUT') and \
               settings.EMAILTIMEOUT is not None:
            est_time = settings.EMAILTIMEOUT * numusers
        else:
            est_time = 1.5 * numusers

        context = {'time': est_time}
        if public_view:
            context['req_id'] = newmsg_request.id
        return render_to_response(self.baseDir()+'finished.html', request, context)


    @aux_call
    @needs_admin
    def commpanel_old(self, request, tl, one, two, module, extra, prog):
        from esp.users.views     import get_user_list
        filterObj, found = get_user_list(request, self.program.getLists(True))

        if not found:
            return filterObj

        sendto_fn_name = request.POST.get('sendto_fn_name', MessageRequest.SEND_TO_SELF_REAL)
        sendto_fn = MessageRequest.assert_is_valid_sendto_fn_or_ESPError(sendto_fn_name)

        listcount = self.approx_num_of_recipients(filterObj, sendto_fn)

        return render_to_response(self.baseDir()+'step2.html', request,
                                              {'listcount': listcount,
                                               'filterid': filterObj.id,
                                               'sendto_fn_name': sendto_fn_name })

    @main_call
    @needs_admin
    def commpanel(self, request, tl, one, two, module, extra, prog):

        usc = UserSearchController()

        context = {}

        #   If list information was submitted, continue to prepare a message
        if request.method == 'POST':
            #   Turn multi-valued QueryDict into standard dictionary
            data = ListGenModule.processPost(request)

            ##  Handle normal list selecting submissions
            if ('base_list' in data and 'recipient_type' in data) or ('combo_base_list' in data):

                selected = usc.selected_list_from_postdata(data)
                filterObj = usc.filter_from_postdata(prog, data)
                sendto_fn_name = usc.sendto_fn_from_postdata(data)
                sendto_fn = MessageRequest.assert_is_valid_sendto_fn_or_ESPError(sendto_fn_name)

                if data['use_checklist'] == '1':
                    (response, unused) = get_user_checklist(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, '/manage/%s/commpanel_old' % prog.getUrlBase())
                    return response

                context['filterid'] = filterObj.id
                context['sendto_fn_name'] = sendto_fn_name
                context['listcount'] = self.approx_num_of_recipients(filterObj, sendto_fn)
                context['selected'] = selected
                return render_to_response(self.baseDir()+'step2.html', request, context)

            ##  Prepare a message starting from an earlier request
            elif 'msgreq_id' in data:
                msgreq = MessageRequest.objects.get(id=data['msgreq_id'])
                context['filterid'] = msgreq.recipients.id
                context['sendto_fn_name'] = msgreq.sendto_fn_name
                sendto_fn = MessageRequest.assert_is_valid_sendto_fn_or_ESPError(msgreq.sendto_fn_name)
                context['listcount'] = self.approx_num_of_recipients(msgreq.recipients, sendto_fn)
                context['from'] = msgreq.sender
                context['subject'] = msgreq.subject
                context['replyto'] = msgreq.special_headers_dict.get('Reply-To', '')
                context['body'] = msgreq.msgtext
                return render_to_response(self.baseDir()+'step2.html', request, context)

            else:
                raise ESPError('What do I do without knowing what kind of users to look for?', log=True)
        else:
            student_search_form = StudentSearchForm()

        context['student_search_form'] = student_search_form
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
        sendto_fn_name = request.POST.get('sendto_fn_name', MessageRequest.SEND_TO_SELF_REAL)
        selected = request.POST.get('selected')
        public_view = 'public_view' in request.POST

        return render_to_response(self.baseDir()+'step2.html', request,
                                              {'listcount': listcount,
                                               'selected': selected,
                                               'filterid': filterid,
                                               'sendto_fn_name': sendto_fn_name,
                                               'from': fromemail,
                                               'replyto': replytoemail,
                                               'subject': subject,
                                               'body': body,
                                               'public_view': public_view})

    class Meta:
        proxy = True
        app_label = 'modules'
