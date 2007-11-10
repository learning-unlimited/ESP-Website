
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_grade, CoreModule
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.users.models    import UserBit, ESPUser, User
from esp.datatree.models import GetNode
from esp.db.models import Q
from esp.middleware   import ESPError

import operator

class StudentRegCore(ProgramModuleObj, CoreModule):

    def students(self, QObject = False):
        verb = GetNode('V/Flags/Public')
        verb2 = GetNode('V/Flags/Registration/Attended')
        STUDREP_VERB = GetNode('V/Flags/UserRole/StudentRep')
        STUDREP_QSC  = GetNode('Q')
        
        qsc  = GetNode("/".join(self.program.anchor.tree_encode()) + "/Confirmation")

        Q_studentrep = Q(userbit__qsc = STUDREP_QSC) & Q(userbit__verb = STUDREP_VERB)

        if QObject:
            return {'confirmed': self.getQForUser(Q(userbit__qsc = qsc) & Q(userbit__verb = verb)),
                    'attended' : self.getQForUser(Q(userbit__qsc = self.program.anchor) &\
                                                  Q(userbit__verb = verb2)),
                    'studentrep': self.getQForUser(Q_studentrep)}
        
        
        return {'confirmed': User.objects.filter(userbit__qsc = qsc, userbit__verb = verb).distinct(),
                'attended' : User.objects.filter(userbit__qsc = self.program.anchor, \
                                                    userbit__verb = verb2).distinct(),
                'studentrep': User.objects.filter(Q_studentrep).distinct()}

    def studentDesc(self):
        return {'confirmed': """Students who have clicked on the `Confirm Pre-Registraiton' button.""",
                'attended' : """Students who attended %s""" % self.program.niceName(),
                'studentrep': """All Student Representatives of ESP"""}

    @needs_student
    @meets_grade
    @meets_deadline()
    def confirmreg(self, request, tl, one, two, module, extra, prog):
	""" The page that is shown once the user saves their student reg,
            giving them the option of printing a confirmation            """
	context = {}
	context['one'] = one
	context['two'] = two

        from esp.money.models import LineItem, LineItemType, RegisterLineItem
        for i in LineItemType.objects.filter(anchor=prog.anchor, optional=False):
            RegisterLineItem(request.user, i)

        context['itemizedcosts'] = LineItem.purchased(prog.anchor, request.user, filter_already_paid=False)
        context['itemizedcosttotal'] = LineItem.purchasedTotalCost(prog.anchor, request.user)
        context['owe_money'] = ( context['itemizedcosttotal'] != 0 )


        if prog.isFull() and not ESPUser(request.user).canRegToFullProgram(prog):
            raise ESPError(log = False), "This program has filled!  It can't accept any more students.  Please try again next session."

	modules = prog.getModules(self.user, tl)
	completedAll = True
	for module in modules:
            if not module.isCompleted() and module.required:
                completedAll = False
            context = module.prepare(context)
	
	if completedAll:
            bit, created = UserBit.objects.get_or_create(user=self.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Confirmation"))
        else:
            raise ESPError(), "You must finish all the necessary steps first, then click on the Save button to finish registration."
            
	receipt = 'program/receipts/'+str(prog.id)+'_custom_receipt.html'
	return render_to_response(receipt, request, (prog, tl), context)


    @needs_student
    @meets_grade    
    @meets_deadline()
    def cancelreg(self, request, tl, one, two, module, extra, prog):
        bits = UserBit.objects.filter(user = self.user,
                                      verb = GetNode('V/Flags/Public'),
                                      qsc  = GetNode('/'.join(prog.anchor.tree_encode())+'/Confirmation'))

        if len(bits) > 0:
            for bit in bits:
                bit.delete()

        return self.goToCore(tl)
  
    @needs_student
    @meets_grade
    @meets_deadline('/MainPage')
    def studentreg(self, request, tl, one, two, module, extra, prog):
    	    """ Display a student reg page """

	    context = {}
            modules = prog.getModules(self.user, 'learn')

	    context['completedAll'] = True
            for module in modules:
                if not module.isCompleted() and module.required:
                    context['completedAll'] = False

                context = module.prepare(context)

            context['canRegToFullProgram'] = ESPUser(request.user).canRegToFullProgram(prog)
                    
	    context['modules'] = modules
	    context['one'] = one
	    context['two'] = two
            context['coremodule'] = self
            context['isConfirmed'] = self.program.isConfirmed(self.user)

	    return render_to_response(self.baseDir()+'mainpage.html', request, (prog, tl), context)

    def isStep(self):
        return False


    def getNavBars(self):
        nav_bars = []
        if True or super(StudentRegCore, self).deadline_met() or ( self.user and self.program and UserBit.objects.UserHasPerms(self.user, self.program, GetNode("V/Deadline/Registration/Classes/OneClass")) ):
             nav_bars.append({ 'link': '/learn/%s/studentreg/' % ( self.program.getUrlBase() ),
                      'text': '%s Student Registration' % ( self.program.niceSubName() ),
                      'section': 'learn'})

        if ESPUser(self.user).isAdmin(self.program):
            nav_bars.append({'link':'/learn/%s/studentreg.html' % (self.program.getUrlBase()),
                             'text':'%s Student Reg Inline Text' % self.program.niceSubName(),
                             'section': 'learn'})

        return nav_bars
    
