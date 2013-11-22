
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
  Email: web-team@lists.learningu.org
"""
from esp.program.modules.base import ProgramModuleObj, needs_student, needs_admin, main_call, aux_call
from esp.web.util        import render_to_response
from esp.users.models   import ESPUser, PersistentQueryFilter, ContactInfo
from esp.users.controllers.usersearch import UserSearchController
from esp.users.views.usersearch import get_user_checklist
from django.db.models.query   import Q
from esp.dbmail.models import ActionHandler
from django.template import Template
from esp.middleware.threadlocalrequest import AutoRequestContext as Context
from esp.middleware import ESPError

from django.conf import settings

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
            "seq": 10
        }

    @aux_call
    @needs_admin
    def grouptextfinal(self, request, tl, one, two, module, extra, prog):
        filterObj = None
        data = {}
        for key in request.POST:
            data[key] = request.POST[key]

        print data


        if not ('base_list' in data and 'recipient_type' in data):
            raise ESPError(), "Corrupted POST data!  Please contact us at "+settings.DEFAULT_EMAIL_ADDRESSES['support']+" and tell us how you got this error, and we'll look into it."

        filterObj = UserSearchController().filter_from_postdata(prog, data)


        numusers = filterObj.getList(ESPUser).distinct().count()

        # TODO: calculate properly
        est_time = 0.5 * numusers

        print 'Sending %d text messages' % numusers
        self.sendMessages(filterObj, data["message"])

        return render_to_response(self.baseDir()+'finished.html', request,
                                  (prog, tl), {'time': est_time})

    @main_call
    @needs_admin
    def grouptextpanel(self, request, tl, one, two, module, extra, prog):
        usc = UserSearchController()

        context = {}
        context['program'] = prog

        context.update(usc.prepare_context(prog))
        context['lists'] = context['lists']['Student']

        # care about enrolled students, students in specific classes, and not really anyone else
        def interesting_list(lst):
          return lst['name'] == 'enrolled' or lst['name'] == 'attended' or lst['name'] == 'all_Student'

        context['lists'] = [lst for lst in context['lists'] if interesting_list(lst)]

        return render_to_response(self.baseDir()+'panel.html', request, (prog, tl), context)

    def sendMessages(self, filterobj, body):
        from twilio.rest import TwilioRestClient

        users = filterobj.getList(ESPUser)
        try:
            users = users.distinct()
        except:
            pass

        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        ourNumbers = settings.TWILIO_ACCOUNT_NUMBERS

        if not account_sid or not auth_token or not ourNumbers:
          raise ESPError(), "You must configure the Twilio account settings before attempting to send texts using this module"

        numberIndex = 0

        for user in users:
            user = ESPUser(user)

            contactInfo = None
            try:
                # TODO: handle multiple ContactInfo objects per user
                contactInfo = ContactInfo.objects.get(user=user)
            except ContactInfo.DoesNotExist:
                pass
            if not contactInfo:
                print "Could not find contact info for "+str(user)
                continue
            # the user has elected to not receive text messages
            if not contactInfo.receive_txt_message:
                print str(user)+" does not want text messages, fine"
                continue
            client = TwilioRestClient(account_sid, auth_token)

            formattedNumber = "+1"+contactInfo.phone_cell.replace("-","")
            print "Sending text message to "+formattedNumber
            client.sms.messages.create(body=body,
                                       to=formattedNumber,
                                       from_=ourNumbers[numberIndex])
            numberIndex = (numberIndex + 1) % len(ourNumbers)

    class Meta:
        abstract = True

