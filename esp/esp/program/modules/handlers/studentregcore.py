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
from argcache            import cache_function
from esp.program.modules.base import ProgramModuleObj, needs_student, meets_deadline, meets_grade, CoreModule, main_call, aux_call, _checkDeadline_helper, meets_cap
from esp.program.modules import module_ext
from esp.program.models  import Program
from esp.program.controllers.confirmation import ConfirmationEmailController
from esp.utils.web import render_to_response
from esp.users.models    import ESPUser, Record
from esp.utils.models import Printer
from esp.accounting.controllers import IndividualAccountingController
from django.db.models.query import Q
from esp.middleware   import ESPError
from decimal import Decimal
from datetime import datetime
from django.db import models
from django.contrib import admin
from django.template import Template
from esp.middleware.threadlocalrequest import AutoRequestContext as Context
from django.http import HttpResponse
from django.template.loader import render_to_string, get_template, select_template
import operator

class StudentRegCore(ProgramModuleObj, CoreModule):
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Student Registration",
            "admin_title": "Core Student Registration",
            "module_type": "learn",
            "seq": -9999,
            "choosable": 1
            }

    @cache_function
    def have_paid(self, user):
        """ Whether the user has paid for this program.  """
        iac = IndividualAccountingController(self.program, user)
        return (iac.has_paid())
    have_paid.depend_on_row('accounting.Transfer', lambda transfer: {'user': transfer.user})
    have_paid.depend_on_row('program.SplashInfo', lambda splashinfo: {'user': splashinfo.student})
    have_paid.depend_on_row('accounting.FinancialAidGrant', lambda grant: {'user': grant.request.user})

    def students(self, QObject = False):
        now = datetime.now()

        q_confirmed = Q(record__event = "reg_confirmed", record__program=self.program)
        q_attended = Q(record__event= "attended", record__program=self.program)
        # if we don't do list(values_list()), it breaks downstream queries for some weird reason I don't understand -WG
        q_checked_out = Q(id__in=list(self.program.currentlyCheckedOutStudents().values_list('id', flat = True)))
        q_checked_in = Q(id__in=list(self.program.currentlyCheckedInStudents().values_list('id', flat = True)))
        q_studentrep = Q(groups__name="StudentRep")

        if QObject:
            retVal = {'confirmed': q_confirmed,
                      'attended' : q_attended,
                      'checked_out': q_checked_out,
                      'checked_in': q_checked_in,
                      'studentrep': q_studentrep}


            if self.program.program_allow_waitlist:
                retVal['waitlisted_students'] = Q(record__event="waitlist",record__program=self.program)

            return retVal

        retVal = {'confirmed': ESPUser.objects.filter(q_confirmed).distinct(),
                  'attended' : ESPUser.objects.filter(q_attended).distinct(),
                  'checked_out': ESPUser.objects.filter(q_checked_out).distinct(),
                  'checked_in': ESPUser.objects.filter(q_checked_in).distinct(),
                  'studentrep': ESPUser.objects.filter(q_studentrep).distinct()}

        if self.program.program_allow_waitlist:
            retVal['waitlisted_students'] = ESPUser.objects.filter(Q(record__event="waitlist",record__program=self.program)).distinct()

        return retVal

    def studentDesc(self):
        retVal = {'confirmed': """Students who have clicked on the `Confirm Registration' button""",
                  'attended' : """Students who attended %s""" % self.program.niceName(),
                  'checked_out': """Students who are currently checked out of %s""" % self.program.niceName(),
                  'checked_in': """Students who are currently checked in to %s""" % self.program.niceName(),
                  'studentrep': """Student Representatives"""}

        if self.program.program_allow_waitlist:
            retVal['waitlisted_students'] = """Students on the program's waitlist"""

        return retVal

    @aux_call
    @needs_student
    @meets_grade
    def waitlist_subscribe(self, request, tl, one, two, module, extra, prog):
        """ Add this user to the waitlist """
        self.request = request

        if prog.user_can_join(request.user):
            raise ESPError("You can't subscribe to the waitlist of a program that isn't full yet!  Please click 'Back' and refresh the page to see the button to confirm your registration.", log=False)

        waitlist = Record.objects.filter(event="waitlist",
                                         user=request.user,
                                         program=prog)

        if waitlist.count() <= 0:
            Record.objects.create(event="waitlist", user=request.user,
                                  program=prog)
            already_on_list = False
        else:
            already_on_list = True

        return render_to_response(self.baseDir()+'waitlist.html', request, { 'already_on_list': already_on_list })

    @aux_call
    @needs_student
    @meets_grade
    def confirmreg(self, request, tl, one, two, module, extra, prog):
        if Record.objects.filter(user=request.user, event="reg_confirmed",program=prog).count() > 0:
            return self.confirmreg_forreal(request, tl, one, two, module, extra, prog, new_reg=False)
        return self.confirmreg_new(request, tl, one, two, module, extra, prog)

    @meets_deadline("/Confirm")
    @meets_cap
    def confirmreg_new(self, request, tl, one, two, module, extra, prog):
        self.request = request

        return self.confirmreg_forreal(request, tl, one, two, module, extra, prog, new_reg=True)

    def confirmreg_forreal(self, request, tl, one, two, module, extra, prog, new_reg):
        """ The page that is shown once the user saves their student reg,
            giving them the option of printing a confirmation            """
        self.request = request

        from esp.program.modules.module_ext import DBReceipt

        iac = IndividualAccountingController(prog, request.user)

        context = {}
        context['one'] = one
        context['two'] = two

        context['itemizedcosts'] = iac.get_transfers()

        user = request.user
        context['finaid'] = user.hasFinancialAid(prog)
        if user.appliedFinancialAid(prog):
            context['finaid_app'] = user.financialaidrequest_set.filter(program=prog).order_by('-id')[0]
        else:
            context['finaid_app'] = None
        context['balance'] = iac.amount_due()

        context['owe_money'] = ( context['balance'] != Decimal("0.0") )

        if not prog.user_can_join(user):
            raise ESPError("This program has filled!  It can't accept any more students.  Please try again next session.", log=False)

        modules = prog.getModules(request.user, tl)
        completedAll = True
        for module in modules:
            if hasattr(module, 'onConfirm'):
                module.onConfirm(request)
            if not module.isCompleted() and module.required:
                completedAll = False
            context = module.prepare(context)

        if completedAll:
            if new_reg:
                rec = Record.objects.create(user=user, event="reg_confirmed",
                                            program=prog)
        else:
            raise ESPError("You must finish all the necessary steps first, then click on the Save button to finish registration.", log=False)

        cfe = ConfirmationEmailController()
        cfe.send_confirmation_email(request.user, self.program)

        try:
            receipt_text = DBReceipt.objects.get(program=self.program, action='confirm').receipt
            context["request"] = request
            context["program"] = prog
            return HttpResponse( Template(receipt_text).render( Context(context, autoescape=False) ) )
        except DBReceipt.DoesNotExist:
            try:
                receipt = 'program/receipts/'+str(prog.id)+'_custom_receipt.html'
                return render_to_response(receipt, request, context)
            except:
                receipt = 'program/receipts/default.html'
                return render_to_response(receipt, request, context)

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Cancel')
    def cancelreg(self, request, tl, one, two, module, extra, prog):
        self.request = request

        from esp.program.modules.module_ext import DBReceipt

        if self.have_paid(request.user):
            raise ESPError("You have already paid for this program!  Please contact us directly (using the contact information in the footer of this page) to cancel your registration and to request a refund.", log=False)

        recs = Record.objects.filter(user=request.user,
                                     event="reg_confirmed",
                                     program=prog)
        for rec in recs:
            rec.delete()

        #   If the appropriate flag is set, remove the student from their classes.
        scrmi = prog.studentclassregmoduleinfo
        if scrmi.cancel_button_dereg:
            sections = request.user.getSections()
            for sec in sections:
                sec.unpreregister_student(request.user)

        #   If a cancel receipt template is there, use it.  Otherwise, return to the main studentreg page.
        try:
            receipt_text = DBReceipt.objects.get(program=self.program, action='cancel').receipt
            context = {}
            context["request"] = request
            context["program"] = prog
            return HttpResponse( Template(receipt_text).render( Context(context, autoescape=False) ) )
        except:
            return self.goToCore(tl)

    @cache_function
    def printer_names():
        return Printer.objects.all().values_list('name', flat=True)
    printer_names.depend_on_model('utils.Printer')
    printer_names = staticmethod(printer_names) # stolen from program.models.getLastProfile, not sure if this is actually the right way to do this?

    @main_call
    @needs_student
    @meets_grade
    @meets_deadline('/MainPage')
    @meets_cap
    def studentreg(self, request, tl, one, two, module, extra, prog):
        """ Display a student reg page """
        self.request = request

        context = {}
        modules = prog.getModules(request.user, 'learn')
        context['completedAll'] = True
        for module in modules:
            # If completed all required modules so far...
            if context['completedAll']:
                if module.isCompleted():
                    module.fillProgressBar = True
                else:
                    if module.required:
                        context['completedAll'] = False

            context = module.prepare(context)

        context['canRegToFullProgram'] = request.user.canRegToFullProgram(prog)


        context['modules'] = modules
        context['one'] = one
        context['two'] = two
        context['coremodule'] = self
        context['scrmi'] = prog.studentclassregmoduleinfo
        context['can_confirm'] = _checkDeadline_helper(None, '/Confirm', self, request, tl)[0]
        context['isConfirmed'] = self.program.isConfirmed(request.user)
        context['have_paid'] = self.have_paid(request.user)
        context['extra_steps'] = "learn:extra_steps"
        context['printers'] = self.printer_names()

        if context['scrmi'] and context['scrmi'].use_priority:
            context['no_confirm'] = True
        else:
            context['no_confirm'] = False

        return render_to_response(self.baseDir()+'mainpage.html', request, context)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
