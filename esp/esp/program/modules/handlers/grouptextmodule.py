
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
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
from esp.users.models   import ESPUser, PersistentQueryFilter, ContactInfo
from esp.users.controllers.usersearch import UserSearchController
from esp.users.forms.generic_search_form import StudentSearchForm
from esp.users.views.usersearch import get_user_checklist
from django.db.models.query   import Q
from esp.dbmail.models import ActionHandler
from django.template import Template
from esp.middleware.threadlocalrequest import AutoRequestContext as Context
from esp.middleware import ESPError

from django.conf import settings

from twilio import TwilioRestException
from twilio.rest import TwilioRestClient

class GroupTextModule(ProgramModuleObj):
    """ Want to tell all enrolled students about a last-minute lunch location
        change? Want to inform students about a cancelled class? The Group Text
        Panel is your friend!
    """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Group Text Panel for Admin",
            "link_title": "Group Text Panel: Text all the students!",
            "module_type": "manage",
            "seq": 10,
            "choosable": 1,
        }

    @staticmethod
    def is_configured():
        """ Check if Twilio configuration settings are set.
            The text message module will not work without them. """

        if not hasattr(settings, 'TWILIO_ACCOUNT_SID') or not isinstance(settings.TWILIO_ACCOUNT_SID, basestring):
            return False
        if not hasattr(settings, 'TWILIO_AUTH_TOKEN') or not isinstance(settings.TWILIO_AUTH_TOKEN, basestring):
            return False
        if not hasattr(settings, 'TWILIO_ACCOUNT_NUMBERS') or (not isinstance(settings.TWILIO_ACCOUNT_NUMBERS, list) and not isinstance(settings.TWILIO_ACCOUNT_NUMBERS, tuple)):
            return False

        return True

    @aux_call
    @needs_admin
    def grouptextfinal(self, request, tl, one, two, module, extra, prog):
        if request.method != 'POST' or 'filterid' not in request.GET or 'message' not in request.POST:
            raise ESPError(), 'Filter or message have not been properly set'

        if not self.is_configured():
            return render_to_response(self.baseDir() + 'not_configured.html', request, {})

        # get the filter to use and text message to send from the request; this is set in grouptextpanel form
        filterObj = PersistentQueryFilter.objects.get(id=request.GET['filterid'])
        message = request.POST['message']
        override = False
        if 'text-override' in request.POST:
            override = request.POST['text-override']

        log = self.sendMessages(filterObj, message, override = override)

        return render_to_response(self.baseDir()+'finished.html', request, {'log': log, 'override': override})

    @main_call
    @needs_admin
    def grouptextpanel(self, request, tl, one, two, module, extra, prog):
        if not self.is_configured():
            return render_to_response(self.baseDir() + 'not_configured.html', request, {})

        usc = UserSearchController()
        context = {}
        context['program'] = prog

        if request.method == "POST":
            data = ListGenModule.processPost(request)
            filterObj = UserSearchController().filter_from_postdata(prog, data)

            context['filterid'] = filterObj.id
            context['num_users'] = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()
            context['est_time'] = float(context['num_users']) * 1.0 / len(settings.TWILIO_ACCOUNT_NUMBERS)
            return render_to_response(self.baseDir()+'options.html', request, context)
        else:
            student_search_form = StudentSearchForm()

        context['student_search_form'] = student_search_form
        context.update(usc.prepare_context(prog, target_path='/manage/%s/grouptextpanel' % prog.url))
        return render_to_response(self.baseDir()+'search.html', request, context)

    @staticmethod
    def sendMessages(filterobj, body, override = False):
        """ Attempts to send a text message with body to users matching filterobj
            Returns a log of actions which can be displayed to user. """

        users = filterobj.getList(ESPUser)
        try:
            users = users.distinct()
        except:
            pass

        if not users:
            raise ESPError(), "Your query did not match any users"

        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        ourNumbers = settings.TWILIO_ACCOUNT_NUMBERS

        if not account_sid or not auth_token or not ourNumbers:
          raise ESPError(), "You must configure the Twilio account settings before attempting to send texts using this module"

        # cycle through our phone numbers to reduce sending time
        numberIndex = 0

        send_log = []
        send_log.append('Sending message to ' + str(users.count()) + ' users')

        for user in users:

            contactInfo = None
            try:
                #   Only get contact info for the actual user (not guardians or emergency contacts)
                contactInfo = ContactInfo.objects.filter(user=user, as_user__isnull=False).distinct('user')[0]
            except ContactInfo.DoesNotExist:
                pass
            if not contactInfo:
                send_log.append("Could not find contact info for "+str(user))
                continue
            send_log.append("Found contact info for "+str(user))

            # the user has elected to not receive text messages
            # unless override is true
            if not contactInfo.receive_txt_message and not override:
                send_log.append(str(user)+" does not want text messages, fine")
                continue
            client = TwilioRestClient(account_sid, auth_token)

            # format the number for Twilio
            formattedNumber = contactInfo.phone_cell.replace("-", "").replace(" ", "")

            if formattedNumber:
                if formattedNumber[0] != '+':
                    formattedNumber = '+1' + formattedNumber

                send_log.append("Sending text message to "+formattedNumber)
                try:
                    client.sms.messages.create(body=body,
                                           to=formattedNumber,
                                           from_=ourNumbers[numberIndex])
                except TwilioRestException as error:
                    send_log.append(error.msg)
                numberIndex = (numberIndex + 1) % len(ourNumbers)

        return "\n".join(send_log)

    class Meta:
        proxy = True
        app_label = 'modules'
