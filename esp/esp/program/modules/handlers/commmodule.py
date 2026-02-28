
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.modules.handlers.listgenmodule import ListGenModule
from esp.utils.web import render_to_response
from esp.dbmail.models import MessageRequest, PlainRedirect
from esp.users.models   import ESPUser, PersistentQueryFilter
from esp.users.controllers.usersearch import UserSearchController
from esp.users.views.usersearch import get_user_checklist
from esp.dbmail.models import ActionHandler
from esp.tagdict.models import Tag
from django.template import Template
from django.template import Context as DjangoContext
from django.template.loader import render_to_string
from esp.middleware import ESPError

import re

# Match /learn/, /teach/, or /volunteer/ + ProgramName/Instance (program url = two path segments)
_PROGRAM_URL_PATTERN = re.compile(
    r'(?:/learn|/teach|/volunteer)/([^/\s\'"<>]+/[^/\s\'"<>]+)',
    re.IGNORECASE
)


def _program_urls_in_text(text, current_program_url):
    """
    Find program URLs in text (e.g. /learn/Splash/2024_Winter/...) that refer to
    a different program than current_program_url (e.g. "Splash/2025_Spring").
    Returns a list of unique program url strings (e.g. ["Splash/2024_Winter"]).
    """
    if not text or not current_program_url:
        return []
    current = current_program_url.strip().rstrip('/')
    found = set()
    for match in _PROGRAM_URL_PATTERN.finditer(text):
        prog_url = match.group(1).strip().rstrip('/')
        if prog_url != current:
            found.add(prog_url)
    return sorted(found)


class CommModule(ProgramModuleObj):
    doc = """Email users that match specific search criteria."""
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
            if not re.match(r'(^.+@{0}$)|(^.+<.+@{0}>$)|(^.+@(\w+\.)?learningu\.org$)|(^.+<.+@(\w+\.)?learningu\.org>$)'.format(settings.SITE_INFO[1].replace('.', '\.')), fromemail):
                raise ESPError("Invalid 'From' email address. The 'From' email address must " +
                               "end in @" + settings.SITE_INFO[1] + " (your website), " +
                               "@learningu.org, or a valid subdomain of learningu.org " +
                               "(i.e., @subdomain.learningu.org).")
        else:
            # Use the info redirect (make one for the default email address if it doesn't exist)
            prs = PlainRedirect.objects.filter(original = "info")
            if not prs.exists():
                redirect = PlainRedirect.objects.create(original = "info", destination = settings.DEFAULT_EMAIL_ADDRESSES['default'])
            fromemail = '%s <%s@%s>' % (Tag.getTag('full_group_name') or '%s %s' % (settings.INSTITUTION_NAME, settings.ORGANIZATION_SHORT_NAME),
                                        "info", settings.SITE_INFO[1])

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

        # Use whichever template the user selected or the default (just an unsubscribe slug) if 'None'
        template = request.POST.get('template', 'default')
        rendered_text = render_to_string('email/{}_email.html'.format(template),
                                        {'msgbody': body})
        # Render the text for the first user
        contextdict = {'user'   : ActionHandler(firstuser, firstuser),
                       'program': ActionHandler(self.program, firstuser),
                       'request': ActionHandler(MessageRequest(), firstuser),
                       'EMAIL_HOST_SENDER': settings.EMAIL_HOST_SENDER}
        rendered_text = Template(rendered_text).render(DjangoContext(contextdict))

        current_program_url = self.program.getUrlBase()
        other_program_urls = _program_urls_in_text(
            (subject or '') + ' ' + (body or ''),
            current_program_url
        )

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
                                               'template': template,
                                               'rendered_text': rendered_text,
                                               'other_program_urls': other_program_urls})

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
        template = request.POST.get('template', 'default')

        current_program_url = self.program.getUrlBase()
        other_program_urls = _program_urls_in_text(
            (subject or '') + ' ' + (body or ''),
            current_program_url
        )
        if other_program_urls and not request.POST.get('confirm_send_with_other_program_links'):
            rendered_text = render_to_string('email/{}_email.html'.format(template),
                                             {'msgbody': body})
            listcount = request.POST.get('listcount', '')
            selected = request.POST.get('selected', '')
            return render_to_response(self.baseDir() + 'preview.html', request, {
                'filterid': filterid,
                'sendto_fn_name': sendto_fn_name,
                'listcount': listcount,
                'selected': selected,
                'subject': subject,
                'from': fromemail,
                'replyto': replytoemail,
                'public_view': public_view,
                'body': body,
                'template': template,
                'rendered_text': rendered_text,
                'other_program_urls': other_program_urls,
                'confirm_send_required': True,
                'program': self.program,
            })

        # Use whichever template the user selected or the default (just an unsubscribe slug) if 'None'
        rendered_text = render_to_string('email/{}_email.html'.format(template),
                                        {'msgbody': body})

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
                                                      msgtext = rendered_text,
                                                      public = public_view,
                                                      special_headers_dict
                                                                 = { 'Reply-To': replytoemail, }, )

        newmsg_request.save()

        context = {}
        if public_view:
            context['req_id'] = newmsg_request.id
        return render_to_response(self.baseDir()+'finished.html', request, context)


    @aux_call
    @needs_admin
    def commpanel_old(self, request, tl, one, two, module, extra, prog):
        from esp.users.views     import get_user_list
        from django.conf import settings

        filterObj, found = get_user_list(request, self.program.getLists(True))

        if not found:
            return filterObj
        context = {}

        context['sendto_fn_name'] = request.POST.get('sendto_fn_name', MessageRequest.SEND_TO_SELF_REAL)
        context['sendto_fn'] = MessageRequest.assert_is_valid_sendto_fn_or_ESPError(context['sendto_fn_name'])

        context['default_from'] = '%s <%s@%s>' % (Tag.getTag('full_group_name') or '%s %s' % (settings.INSTITUTION_NAME, settings.ORGANIZATION_SHORT_NAME),
                                              "info", settings.SITE_INFO[1])
        context['from'] = context['default_from']

        context['listcount'] = self.approx_num_of_recipients(filterObj, context['sendto_fn'])
        context['filterid'] = filterObj.id

        # Use the info redirect (make one for the default email address if it doesn't exist)
        prs = PlainRedirect.objects.filter(original = "info")

        if not prs.exists():
           redirect = PlainRedirect.objects.create(original = "info", destination = settings.DEFAULT_EMAIL_ADDRESSES['default'])

        return render_to_response(self.baseDir()+'step2.html', request, context)


    @main_call
    @needs_admin
    def commpanel(self, request, tl, one, two, module, extra, prog):
        from django.conf import settings

        usc = UserSearchController()

        context = {}

        #   If list information was submitted, continue to prepare a message
        if request.method == 'POST':
            #   Turn multi-valued QueryDict into standard dictionary
            data = ListGenModule.processPost(request)
            context['default_from'] = '%s <%s@%s>' % (Tag.getTag('full_group_name') or '%s %s' % (settings.INSTITUTION_NAME, settings.ORGANIZATION_SHORT_NAME),
                                                      "info", settings.SITE_INFO[1])
            ##  Handle normal list selecting submissions
            if ('base_list' in data and 'recipient_type' in data) or ('combo_base_list' in data):

                selected = usc.selected_list_from_postdata(data)
                filterObj = usc.filter_from_postdata(prog, data)
                sendto_fn_name = usc.sendto_fn_from_postdata(data)
                sendto_fn = MessageRequest.assert_is_valid_sendto_fn_or_ESPError(sendto_fn_name)

                if data['use_checklist'] == '1':
                    (response, unused) = get_user_checklist(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, '/manage/%s/commpanel_old' % prog.getUrlBase(), extra_context = {'module': "Communications Portal"})
                    return response

                context['filterid'] = filterObj.id
                context['sendto_fn_name'] = sendto_fn_name
                context['listcount'] = self.approx_num_of_recipients(filterObj, sendto_fn)
                context['selected'] = selected
                # Use the info redirect (make one for the default email address if it doesn't exist)
                prs = PlainRedirect.objects.filter(original = "info")
                if not prs.exists():
                    redirect = PlainRedirect.objects.create(original = "info", destination = settings.DEFAULT_EMAIL_ADDRESSES['default'])
                context['from'] = context['default_from']
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

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
