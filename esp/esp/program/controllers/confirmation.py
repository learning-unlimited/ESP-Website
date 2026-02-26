
from __future__ import absolute_import
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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

from esp.program.models import Program, ClassSection, ClassSubject
from esp.users.models import ESPUser, Record, RecordType
from esp.program.modules.module_ext import DBReceipt
from esp.program.modules.forms.admincore import get_template_source

from django.template import Template, Context
from django.template.loader import select_template
from esp.dbmail.models import send_mail

class ConfirmationEmailController(object):
    def send_confirmation_email(self, user, program, repeat=False, override=False, context = {}):
        options = program.studentclassregmoduleinfo
        ## Get or create a userbit indicating whether or not email's been sent.
        try:
            rt = RecordType.objects.get(name="conf_email")
            record, created = Record.objects.get_or_create(user=user, event=rt, program=program)
        except Exception:
            created = False
        if (created or repeat) and (options.send_confirmation or override):
            context['user'] = user
            context['program'] = program
            receipt = select_template(['program/confemails/%s_custom_receipt.html' %(program.id), 'program/confemails/default.html'])
            # render the custom pretext first
            try:
                pretext = DBReceipt.objects.get(program=program, action='confirmemail').receipt
            except DBReceipt.DoesNotExist:
                pretext = get_template_source(['program/confemails/%s_custom_pretext.html' %(program.id), 'program/confemails/default_pretext.html'])
            context['pretext'] = Template(pretext).render( Context(context, autoescape=False) )
            receipt_text = receipt.render( context )
            send_mail("Thank you for registering for %s!" %(program.niceName()), \
                      receipt_text, \
                      (ESPUser.email_sendto_address(program.director_email, program.niceName() + " Directors")), \
                      [user.email], True)

