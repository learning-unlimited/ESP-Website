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

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string

from esp.dbmail.models import send_mail
from esp.program.models import (
    ClassSubject,
    EXTENDED_BUDGET_STATUS_PENDING,
    EXTENDED_BUDGET_STATUS_APPROVED,
    EXTENDED_BUDGET_STATUS_REJECTED,
)
from esp.program.modules.admin_search import AdminSearchEntry
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.users.models import ESPUser
from esp.utils.web import render_to_response


class ExtendedBudgetModule(ProgramModuleObj):
    doc = """View and approve extended budget requests."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Extended Budget Requests",
            "link_title": "Extended Budget Requests",
            "module_type": "manage",
            "seq": 30,
            "choosable": 0,
        }

    @classmethod
    def get_admin_search_entry(cls, program, tl, view_name, pmo):
        if view_name != "extendedbudget":
            return None
        base = program.getUrlBase()
        return AdminSearchEntry(
            id="manage_extendedbudget",
            url="/manage/%s/extendedbudget" % base,
            title="Extended Budget Requests",
            category="Logistics",
            keywords=["budget", "extended", "reimbursement", "requests"],
        )

    def isStep(self):
        return False

    def _send_status_email(self, cls, status_label):
        subject = "[%s] Extended budget request %s: %s" % (
            cls.parent_program.niceName(),
            status_label.lower(),
            cls.title,
        )
        email_context = {
            'class': cls,
            'program': cls.parent_program,
            'status_label': status_label,
            'DEFAULT_HOST': settings.DEFAULT_HOST,
        }
        email_contents = render_to_string(
            'program/modules/extendedbudgetmodule/status_email.txt',
            email_context,
        )
        recipients = [teacher.get_email_sendto_address() for teacher in cls.get_teachers()]
        if not recipients:
            return
        from_email = cls.parent_program.director_email or settings.DEFAULT_EMAIL_ADDRESSES['default']
        from_email = ESPUser.email_sendto_address(from_email, f'{cls.parent_program.program_type} Class Registration')
        send_mail(subject, email_contents, from_email, recipients, False)

    class Meta:
        proxy = True
        app_label = 'modules'

    @main_call
    @needs_admin
    def extendedbudget(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            action = request.POST.get('action')
            class_id = request.POST.get('class_id')
            if action in ('approve', 'reject') and class_id:
                try:
                    cls = ClassSubject.objects.get(id=int(class_id), parent_program=prog)
                except (ValueError, ClassSubject.DoesNotExist):
                    cls = None
                if cls:
                    previous_status = cls.extended_budget_status
                    if previous_status != EXTENDED_BUDGET_STATUS_PENDING:
                        messages.error(
                            request,
                            "Extended budget request for '%s' has already been finalized." % cls.title,
                        )
                    else:
                        if action == 'approve':
                            cls.extended_budget_status = EXTENDED_BUDGET_STATUS_APPROVED
                            messages.success(
                                request,
                                "Extended budget request for '%s' approved." % cls.title,
                            )
                            status_label = "Approved"
                        else:
                            cls.extended_budget_status = EXTENDED_BUDGET_STATUS_REJECTED
                            messages.success(
                                request,
                                "Extended budget request for '%s' rejected." % cls.title,
                            )
                            status_label = "Rejected"
                        cls.save()
                        self._send_status_email(cls, status_label)
                else:
                    messages.error(request, "Unable to find that class for this program.")
            else:
                messages.error(request, "Invalid request.")
            return HttpResponseRedirect(request.get_full_path())

        pending_requests = ClassSubject.objects.filter(
            parent_program=prog,
            extended_budget_status=EXTENDED_BUDGET_STATUS_PENDING,
        ).order_by('title', 'id')

        context = {
            'program': prog,
            'pending_requests': pending_requests,
        }
        return render_to_response(self.baseDir() + 'extendedbudget.html', request, context)
