
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
from esp.users.models import ESPUser, Record
from esp.program.modules.module_ext import DBReceipt

from django.template import Template, Context
from django.template.loader import select_template
from esp.dbmail.models import send_mail

class ConfirmationEmailController(object):
    def send_confirmation_email(self, user, program, repeat=False, override=False):
        options = program.studentclassregmoduleinfo
        ## Get or create a userbit indicating whether or not email's been sent.
        try:
            record, created = Record.objects.get_or_create(user=user, event="conf_email", program=program)
        except Exception:
            created = False
        if (created or repeat) and (options.send_confirmation or override):
            try:
                receipt_template = Template(DBReceipt.objects.get(program=program, action='confirmemail').receipt)
            except:
                receipt_template = select_template(['program/confemails/%s_confemail.txt' %(program.id),'program/confirm_email.txt'])
            send_mail("Thank you for registering for %s!" %(program.niceName()), \
                      receipt_template.render(Context({'user': user, 'program': program}, autoescape=False)), \
                      ("%s <%s>" %(program.niceName() + " Directors", program.director_email)), \
                      [user.email], True)

