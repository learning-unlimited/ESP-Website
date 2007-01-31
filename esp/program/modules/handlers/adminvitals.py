from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.data        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.program.models import Class, Program
from esp.users.models import UserBit, ESPUser

class AdminVitals(ProgramModuleObj):

        
    def prepare(self, context={}):
        import operator
        
        classes = self.program.classes()
        vitals = {'classtotal': classes.count()}
        classes = list(classes)
        
        vitals['classapproved'] = len([x for x in classes if x.isAccepted() ])
        vitals['classunreviewed'] = len([x for x in classes if not x.isReviewed() ])

        vitals['classrejected'] = vitals['classtotal'] - vitals['classapproved'] - vitals['classunreviewed']


        vitals['teachernum'] = self.program.teachers().items()
        vitals['teachernum'].append(('total', self.program.teachers_union()))
        vitals['studentnum'] = self.program.students().items()
        vitals['studentnum'].append(('total', self.program.students_union()))
        
        timeslots = self.program.getTimeSlots()

        vitals['timeslots'] = []
        
        for timeslot in timeslots:
            curTimeslot = {'slotname': timeslot.friendly_name}
            
            curclasses = Class.objects.filter(parent_program = self.program,
                                              meeting_times  = timeslot)

            curTimeslot['classcount'] = curclasses.count()

            if curTimeslot['classcount'] == 0:
                curTimeslot['studentcount'] = 0
            else:
                curTimeslot['studentcount'] = \
                      reduce(operator.add, [x.num_students() for x in curclasses ])
            
            vitals['timeslots'].append(curTimeslot)

        context['vitals'] = vitals
        
        return context
    
 
