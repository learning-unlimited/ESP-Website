
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_grade, CoreModule, main_call, aux_call
from esp.program.modules import module_ext
from esp.program.models  import Program
from esp.web.util        import render_to_response
from esp.users.models    import UserBit, ESPUser, User
from esp.datatree.models import *
from django.db.models.query import Q
from esp.middleware   import ESPError
from esp.accounting_docs.models import Document
from esp.accounting_core.models import LineItemType, EmptyTransactionException
from decimal import Decimal
from datetime import datetime
from django.db import models
from django.contrib import admin
from django.template import Context, Template
from django.http import HttpResponse
from esp.lib.markdown import markdown
import operator

class StudentRegCore(ProgramModuleObj, CoreModule):
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Student Registration",
            "admin_title": "Core Student Registration",
            "module_type": "learn",
            "seq": -9999
            }

    def have_paid(self):
        """ Whether the user has paid for this program or its parent program. Duplicated from creditcardmodule_cybersource. """
        if ( Document.objects.filter(user=self.user, anchor=self.program_anchor_cached(), txn__complete=True).count() > 0 ):
            return True
        else:
            parent_program = self.program.getParentProgram()
            if parent_program is not None:
                return ( Document.objects.filter(user=self.user, anchor=parent_program.anchor, txn__complete=True).count() > 0 )

    def students(self, QObject = False):
        verb = GetNode('V/Flags/Public')
        verb2 = GetNode('V/Flags/Registration/Attended')
        STUDREP_VERB = GetNode('V/Flags/UserRole/StudentRep')
        STUDREP_QSC  = GetNode('Q')
        
        qsc  = GetNode("/".join(self.program_anchor_cached().tree_encode()) + "/Confirmation")
        qsc_waitlist = GetNode("/".join(self.program_anchor_cached().tree_encode()) + "/Waitlist")

        Q_studentrep = Q(userbit__qsc = STUDREP_QSC) & Q(userbit__verb = STUDREP_VERB)

        if QObject:
            return {'confirmed': self.getQForUser(Q(userbit__qsc = qsc) & Q(userbit__verb = verb)),
                    'attended' : self.getQForUser(Q(userbit__qsc = self.program_anchor_cached()) &\
                                                  Q(userbit__verb = verb2)),
                    'studentrep': self.getQForUser(Q_studentrep),
                    'waitlisted_students': self.getQForUser(Q(userbit__qsc = qsc_waitlist) & Q(userbit__verb = verb))}
        
        
        return {'confirmed': User.objects.filter(userbit__qsc = qsc, userbit__verb = verb).distinct(),
                'attended' : User.objects.filter(userbit__qsc = self.program_anchor_cached(), \
                                                    userbit__verb = verb2).distinct(),
                'studentrep': User.objects.filter(Q_studentrep).distinct(),
                'waitlisted_students': User.objects.filter(userbit__qsc = qsc_waitlist, userbit__verb = verb).distinct()}

    def studentDesc(self):
        return {'confirmed': """Students who have clicked on the `Confirm Pre-Registration' button.""",
                'attended' : """Students who attended %s""" % self.program.niceName(),
                'studentrep': """All Student Representatives of ESP"""}

    @aux_call
    @needs_student
    @meets_grade
    def waitlist_subscribe(self, request, tl, one, two, module, extra, prog):
        """ Add this user to the waitlist """
        if not self.program.isFull():
            raise ESPError(False), "You can't subscribe to the waitlist of a program that isn't full yet!  Please click 'Back' and refresh the page to see the button to confirm your registration."

        waitlist_all = UserBit.objects.filter(verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Waitlist")).filter(enddate__gte=datetime.now())
        waitlist = waitlist_all.filter(user=self.user)
        
        if waitlist.count() <= 0:
            UserBit.objects.create(user=self.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Waitlist"), recursive=False)
            already_on_list = False
        else:
            already_on_list = True

        return render_to_response(self.baseDir()+'waitlist.html', request, (prog, tl), { 'already_on_list': already_on_list, 'waitlist': waitlist_all })
        
    @aux_call
    @needs_student
    @meets_grade
    def confirmreg(self, request, tl, one, two, module, extra, prog):
        if UserBit.objects.filter(user=self.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Confirmation")).filter(enddate__gte=datetime.now()).count() > 0:
            return self.confirmreg_forreal(request, tl, one, two, module, extra, prog, new_reg=False)
        return self.confirmreg_new(request, tl, one, two, module, extra, prog)
    
    @meets_deadline("/Confirm")
    def confirmreg_new(self, request, tl, one, two, module, extra, prog):
        return self.confirmreg_forreal(request, tl, one, two, module, extra, prog, new_reg=True)
    
    def confirmreg_forreal(self, request, tl, one, two, module, extra, prog, new_reg):
        """ The page that is shown once the user saves their student reg,
            giving them the option of printing a confirmation            """
        from esp.program.modules.module_ext import DBReceipt

        try:
            invoice = Document.get_invoice(request.user, prog.anchor, LineItemType.objects.filter(anchor=GetNode(prog.anchor.get_uri()+'/LineItemTypes/Required')), dont_duplicate=True, get_complete=True)
        except:
            invoice = Document.get_invoice(request.user, prog.anchor, LineItemType.objects.filter(anchor=GetNode(prog.anchor.get_uri()+'/LineItemTypes/Required')), dont_duplicate=True)

        #   Why is get_complete false?
        receipt = Document.get_receipt(request.user, prog.anchor, [], get_complete=False)

        context = {}
        context['one'] = one
        context['two'] = two

        context['itemizedcosts'] = invoice.get_items()

        context['finaid'] = ESPUser(request.user).hasFinancialAid(prog.anchor)

        try:
            context['balance'] = Decimal("%0.2f" % invoice.cost())
        except EmptyTransactionException:
            context['balance'] = Decimal("0.0")
            
        context['owe_money'] = ( context['balance'] != Decimal("0.0") )

        if prog.isFull() and not ESPUser(request.user).canRegToFullProgram(prog) and not self.program.isConfirmed(self.user):
            raise ESPError(log = False), "This program has filled!  It can't accept any more students.  Please try again next session."

        modules = prog.getModules(self.user, tl)
        completedAll = True
        for module in modules:
            if hasattr(module, 'onConfirm'):
                module.onConfirm(request) 
            if not module.isCompleted() and module.required:
                completedAll = False
            context = module.prepare(context)
        
        if completedAll:
            if new_reg:
                bit = UserBit.objects.create(user=self.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Confirmation"))
        else:
            raise ESPError(False), "You must finish all the necessary steps first, then click on the Save button to finish registration."
            
        try:
            receipt_text = DBReceipt.objects.get(program=self.program, action='confirm').receipt
            context["request"] = request
            context["program"] = prog
            return HttpResponse( Template(receipt_text).render( Context(context, autoescape=False) ) )
        except DBReceipt.DoesNotExist:
            receipt = 'program/receipts/'+str(prog.id)+'_custom_receipt.html'
            return render_to_response(receipt, request, (prog, tl), context)

    @aux_call
    @needs_student
    @meets_grade    
    @meets_deadline()
    def cancelreg(self, request, tl, one, two, module, extra, prog):
        from esp.program.modules.module_ext import DBReceipt
        
        if self.have_paid():
            raise ESPError(False), "You have already paid for this program!  Please contact us directly (using the contact information in the footer of this page) to cancel your registration and to request a refund."
        
        bits = UserBit.objects.filter(user = self.user,
                                      verb = GetNode('V/Flags/Public'),
                                      qsc  = GetNode('/'.join(prog.anchor.tree_encode())+'/Confirmation'))

        if len(bits) > 0:
            for bit in bits:
                bit.expire()

        #   If the appropriate flag is set, remove the student from their classes.
        scrmi = prog.getModuleExtension('StudentClassRegModuleInfo')
        if scrmi.cancel_button_dereg:
            sections = self.user.getSections()
            for sec in sections:
                sec.unpreregister_student(self.user)

        #   If a cancel receipt template is there, use it.  Otherwise, return to the main studentreg page.
        try:
            receipt_text = DBReceipt.objects.get(program=self.program, action='cancel').receipt
            context = {}
            context["request"] = request
            context["program"] = prog
            return HttpResponse( Template(receipt_text).render( Context(context, autoescape=False) ) )
        except:
            return self.goToCore(tl)

    @main_call
    @needs_student
    @meets_grade
    @meets_deadline('/MainPage')
    def studentreg(self, request, tl, one, two, module, extra, prog):
        """ Display a student reg page """

        context = {}
        modules = prog.getModules(self.user, 'learn')
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
        context['scrmi'] = prog.getModuleExtension('StudentClassRegModuleInfo')
        context['isConfirmed'] = self.program.isConfirmed(self.user)            
        context['have_paid'] = self.have_paid()
        
        context['printers'] = [ x.name for x in GetNode('V/Publish/Print').children() ]

        return render_to_response(self.baseDir()+'mainpage.html', request, (prog, tl), context)

    def isStep(self):
        return False


    def getNavBars(self):
        nav_bars = []
        if super(StudentRegCore, self).deadline_met() or ( self.user and self.program and UserBit.objects.UserHasPerms(self.user, self.program, GetNode("V/Deadline/Registration/Student/Classes/OneClass")) ):
             nav_bars.append({ 'link': '/learn/%s/studentreg/' % ( self.program.getUrlBase() ),
                      'text': '%s Student Registration' % ( self.program.niceSubName() ),
                      'section': ''})

        if ESPUser(self.user).isAdmin(self.program):
            nav_bars.append({'link':'/learn/%s/studentreg.html' % (self.program.getUrlBase()),
                             'text':'%s Student Reg Inline Text' % self.program.niceSubName(),
                             'section': 'learn'})

        return nav_bars
    
