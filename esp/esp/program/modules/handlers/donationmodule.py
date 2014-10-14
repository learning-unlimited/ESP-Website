
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2014 by the individual contributors
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

from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call
from esp.datatree.models import *
from esp.web.util import render_to_response
from esp.dbmail.models import send_mail
from esp.users.models import ESPUser
from esp.tagdict.models import Tag
from esp.accounting.models import LineItemType
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request

from django.conf import settings
from django.db import transaction
from django.db.models.query import Q
from django.http import HttpResponseRedirect
from django.contrib.sites.models import Site
from django.template.loader import render_to_string

from decimal import Decimal
from datetime import datetime
import stripe
import json
import re

class DonationModule(ProgramModuleObj):

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Donation Module",
            "link_title": "Optional Donation",
            "module_type": "learn",
            "seq": 50,
            }

    def apply_settings(self):
        #   Rather than using a model in module_ext.*, configure the module
        #   from a Tag (which can be per-program or global), combining the
        #   Tag's specifications with defaults in the code.
        DEFAULTS = {
            'donation_text': 'Donation to Learning Unlimited',
            'donation_options': [10, 20, 50],
        }
        tag_data = json.loads(Tag.getProgramTag('donation_settings', self.program, "{}"))
        self.settings = DEFAULTS.copy()
        self.settings.update(tag_data)
        return self.settings

    def get_setting(self, name, default=None):
        return self.apply_settings().get(name, default)

    def line_item_type(self):
        pac = ProgramAccountingController(self.program)
        (donate_type, created) = pac.get_lineitemtypes().get_or_create(text=self.get_setting('donation_text'))
        return donate_type

    def isCompleted(self):
        """ Whether the user has paid for this program or its parent program. """
        iac = IndividualAccountingController(self.program, get_current_request().user)
        return (len(iac.get_preferences([self.line_item_type(),])) > 0)

    def students(self, QObject = False):
        QObj = Q(transfer__line_item=self.line_item_type())

        if QObject:
            return {'donation': QObj}
        else:
            return {'donation': ESPUser.objects.filter(QObj).distinct()}

    def studentDesc(self):
        return {'donation': """Students who have chosen to make an optional donation."""}

    @main_call
    @usercheck_usetl
    @meets_deadline('/ExtraCosts')
    def donation(self, request, tl, one, two, module, extra, prog):

        user = ESPUser(request.user)

        iac = IndividualAccountingController(self.program, user)
        context = {}
        context['module'] = self
        context['program'] = prog
        context['user'] = user

        #   Load donation amount separately, since the client-side code needs to know about it separately.
        donation_prefs = iac.get_preferences([self.line_item_type(),])
        if donation_prefs:
            context['amount_donation'] = Decimal(donation_prefs[0][2])
            context['has_donation'] = True
        else:
            context['amount_donation'] = Decimal('0.00')
            context['has_donation'] = False
        context['institution'] = settings.INSTITUTION_NAME

        return render_to_response(self.baseDir() + 'donation.html', request, context)

    class Meta:
        proxy = True

