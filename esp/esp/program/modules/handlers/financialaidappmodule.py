
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call
from esp.program.modules import module_ext
from esp.utils.web import render_to_response, secure_required
from esp.middleware      import ESPError
from esp.users.models    import ESPUser, User
from django.db.models.query       import Q
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from esp.program.models  import FinancialAidRequest
from esp.tagdict.models import Tag
from django.conf import settings
from esp.middleware.threadlocalrequest import get_current_request
from django              import forms


# student class picker module
class FinancialAidAppModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Financial Aid Application",
            "link_title": "Financial Aid Application",
            "module_type": "learn",
            "seq": 25,
            "choosable": 0,
            }

    def students(self, QObject = False):
        Q_students = Q(financialaidrequest__program = self.program)

        Q_students_complete = Q(financialaidrequest__done = True)
        Q_students_approved = Q(financialaidrequest__financialaidgrant__percent__isnull=False) | Q(financialaidrequest__financialaidgrant__amount_max_dec__isnull=False)

        if QObject:
            return {'studentfinaid_complete': Q_students & Q_students_complete,
                    'studentfinaid':          Q_students,
                    'studentfinaid_approved': Q_students & Q_students_approved}
        else:
            return {'studentfinaid_complete': ESPUser.objects.filter(Q_students & Q_students_complete),
                    'studentfinaid':          ESPUser.objects.filter(Q_students),
                    'studentfinaid_approved': ESPUser.objects.filter(Q_students & Q_students_approved)}


    def studentDesc(self):
        return {'studentfinaid_complete': """Students who have completed a financial aid application""",
                'studentfinaid':          """Students who have started a financial aid application""",
                'studentfinaid_approved': """Students who have been granted financial aid"""}

    def isCompleted(self):
        return get_current_request().user.appliedFinancialAid(self.program)

    @main_call
    @needs_student
    @meets_deadline('/Finaid')
    @method_decorator(secure_required)
    # I didn't set @meets_cap here, because I don't want a bug in that to be
    # misinterpreted as "we are out of financial aid".
    def finaid(self,request, tl, one, two, module, extra, prog):
        """
        A way for a student to apply for financial aid.
        """
        from datetime import datetime
        from esp.dbmail.models import send_mail

        app, created = FinancialAidRequest.objects.get_or_create(user = request.user,
                                                                program = self.program)

        class Form(forms.ModelForm):
            class Meta:
                model = FinancialAidRequest
                tag_data = Tag.getTag('finaid_form_fields')
                if tag_data:
                    fields = tuple(field.strip() for field in tag_data.split(',') if hasattr(FinancialAidRequest(), field.strip()))
                else:
                    fields = '__all__'

        if request.method == 'POST':
            form = Form(request.POST, initial = app.__dict__)
            if form.is_valid():
                app.__dict__.update(form.cleaned_data)

                if not 'submitform' in request.POST or request.POST['submitform'].lower() == 'complete':
                    app.done = True
                elif request.POST['submitform'].lower() == 'mark as incomplete' or request.POST['submitform'].lower() == 'save progress':
                    app.done = False
                else:
                    raise ESPError("Our server lost track of whether or not you were finished filling out this form.  Please go back and click 'Complete' or 'Mark as Incomplete'.")

                app.save()

                # Send an email announcing the application
                date_str = str(datetime.now())
                subj_str = '%s %s applied for Financial Aid for %s' % (request.user.first_name, request.user.last_name, prog.niceName())
                msg_str = "\n%s %s applied for Financial Aid for %s on %s."
                send_mail(subj_str, (msg_str +
                """

Here is their form data:

========================================
Program:  %s
User:  %s %s <%s>
Approved:  %s
Has Reduced Lunch:  %s
Household Income:  $%s
Form Was Filled Out by Non-Student:  %s
Extra Explanation:
%s

========================================

This request can be (re)viewed at:
<http://%s/admin/program/financialaidrequest/%s/>


""") % (request.user.first_name,
    request.user.last_name,
    prog.niceName(),
    date_str,
    str(app.program),
    request.user.first_name,
    request.user.last_name,
    str(app.user),
    date_str,
    str(app.reduced_lunch),
    str(app.household_income),
    str(app.student_prepare),
    app.extra_explaination,
    settings.DEFAULT_HOST, # server hostname
    str(app.id)),
                            settings.SERVER_EMAIL,
                            [ prog.getDirectorConfidentialEmail() ] )
                # Automatically accept apps for people with subsidized lunches
                if app.reduced_lunch:
                    app.approve()
                return self.goToCore(tl)

        else:
            form = Form(initial = app.__dict__)

        return render_to_response(self.baseDir()+'application.html',
                                  request,
                                  {'form': form, 'app': app})


    class Meta:
        proxy = True
        app_label = 'modules'
