from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.data        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.program.models import Class, Program
from esp.users.models import UserBit, ESPUser

class AdminVitals(ProgramModuleObj):

        
    def prepare(self, context={}):
        import operator
        classes = Class.objects.filter(parent_program = self.program)
        vitals = {'classtotal': len(classes)}

        vitals['classapproved'] = len([x for x in classes if x.isAccepted() ])
        vitals['classrejected'] = vitals['classtotal'] - vitals['classapproved']

        vitals['teachernum'] = len(self.program.teachers())
        vitals['studentnum'] = len(self.program.students())

        timeslots = self.program.getTimeSlots()

        vitals['timeslots'] = []
        
        for timeslot in timeslots:
            curTimeslot = {'slotname': timeslot.friendly_name}
            
            curclasses = Class.objects.filter(parent_program = self.program,
                                              meeting_times  = timeslot)

            curTimeslot['classcount'] = curclasses.count()

            curTimeslot['studentcount'] = \
                              reduce(operator.add, [x.num_students() for x in curclasses ])
            
            vitals['timeslots'].append(curTimeslot)

        context['vitals'] = vitals
        
        return context
    
 
