from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.program.modules import module_ext
from esp.web.data        import render_to_response
from esp.users.models    import UserBit, ESPUser
from esp.datatree.models import GetNode
from django.db.models import Q
import operator

class StudentRegCore(ProgramModuleObj):


    def students(self, QObject = False):
        verb = GetNode('V/Flags/Public')
        qsc  = GetNode("/".join(self.program.anchor.tree_encode()) + "/Confirmation")
        if QObject:
            return {'confirmed': Q(userbit__qsc = qsc) & Q(userbit__verb = verb)}
        
        return {'confirmed': ESPUser.objects.filter(userbit__qsc = qsc, userbit__verb = verb).distinct()}

    def studentDesc(self):
        return {'confirmed': """This is a list of students who have clicked on the `Confirm Pre-Registraiton' button."""}

    @needs_student
    @meets_deadline()
    def confirmreg(self, request, tl, one, two, module, extra, prog):
	""" The page that is shown once the user saves their student reg,
            giving them the option of printing a confirmation            """
	context = {}
	context['one'] = one
	context['two'] = two

	modules = prog.getModules(self.user, tl)
	completedAll = True
	for module in modules:
            if not module.isCompleted() and module.required:
                completedAll = False
			
	
	if completedAll:
            bit, created = UserBit.objects.get_or_create(user=self.user, verb=GetNode("V/Flags/Public"), qsc=GetNode("/".join(prog.anchor.tree_encode()) + "/Confirmation"))
        else:
            assert False, "Error: You did not finish all necessary steps!"
            
	receipt = 'program/receipts/'+str(prog.id)+'_custom_receipt.html'
	return render_to_response(receipt, request, (prog, tl), context)


    @needs_student
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
    @meets_deadline()
    def studentreg(self, request, tl, one, two, module, extra, prog):
    	    """ Display a student reg page """
	    context = {}
            modules = prog.getModules(self.user, 'learn')

	    context['completedAll'] = True
            for module in modules:
                if not module.isCompleted() and module.required:
                    context['completedAll'] = False

                context = module.prepare(context)

                    
	    context['modules'] = modules
	    context['one'] = one
	    context['two'] = two
            context['coremodule'] = self
            context['isConfirmed'] = self.program.isConfirmed(self.user)

	    return render_to_response(self.baseDir()+'mainpage.html', request, (prog, tl), context)

    def isStep(self):
        return False

