
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.datatree.models import GetNode, DataTree
from esp.program.models  import Class, ClassCategories, RegistrationProfile
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.middleware      import ESPError
from esp.users.models    import ESPUser, UserBit, User
from esp.db.models       import Q
from django.template.loader import get_template
from esp.cal.models import Event

# student class picker module
class StudentClassRegModule(ProgramModuleObj):

    def extensions(self):
        """ This function gives all the extensions...that is, models that act on the join of a program and module."""
        return [('classRegInfo', module_ext.StudentClassRegModuleInfo)] # ClassRegModuleInfo has important information for this module


    def students(self, QObject = False):
        from esp.program.models import Class
        Conf = Q(userbit__qsc__parent = self.program.classes_node()) & \
               Q(userbit__verb = GetNode('V/Flags/Registration/Confirmed'))

        Prel = Q(userbit__qsc__parent = self.program.classes_node()) & \
               Q(userbit__verb = GetNode('V/Flags/Registration/Preliminary'))
        
        if QObject:
            return {'classreg': self.getQForUser(Conf | Prel)}
        else:
            return {'classreg': User.objects.filter((Conf | Prel)).distinct()}


    def studentDesc(self):
        return {'classreg': """Students who have are enrolled in at least one class."""}
    
    def isCompleted(self):
        self.user = ESPUser(self.user)
        if self.user.getEnrolledClasses(self.program).count() == 0:
            return False
        return (self.user.getEnrolledClasses(self.program).count() > 0) and (UserBit.UserHasPerms(self.user, self.program.anchor_id, GetNode('V/Deadline/Registration/Student/Classes')))

    def deadline_met(self):
        #tmpModule = ProgramModuleObj()
        #tmpModule.__dict__ = self.__dict__
        return super(StudentClassRegModule, self).deadline_met('/Classes/OneClass')

    
    @needs_student
    def prepare(self, context={}):
	regProf = RegistrationProfile.getLastForProgram(self.user, self.program)
	timeslots = list(self.program.getTimeSlots().order_by('id'))
	classList = regProf.preregistered_classes()

        prevTimeSlot = None
        blockCount = 0

        schedule = []
        timeslot_dict = {}
        for cls in classList:
            for mt in cls.meeting_times.all().values('id'):
                timeslot_dict.update({mt['id']: cls})
            
        for timeslot in timeslots:
            if prevTimeSlot != None:
                if not Event.contiguous(prevTimeSlot, timeslot):
                    blockCount += 1

            if timeslot.id in timeslot_dict:
                schedule.append((timeslot, timeslot_dict[timeslot.id], blockCount + 1))
            else:
                schedule.append((timeslot, None, blockCount + 1))

            prevTimeSlot = timeslot
                
        context['timeslots'] = schedule
        
	return context

    @needs_student
    @meets_deadline('/Classes/OneClass')
    def addclass(self,request, tl, one, two, module, extra, prog):
        """ Preregister a student for the specified class, then return to the studentreg page """

        if request.POST.has_key('class_id'):
            classid = request.POST['class_id']
        else:
            from esp.dblog.models import error
            raise ESPError(), "We've lost track of your chosen class's ID!  Please try again; make sure that you've clicked the \"Add Class\" button, rather than just typing in a URL.  Also, please make sure that your Web browser has JavaScript enabled."

        if ( not UserBit.objects.UserHasPerms(request.user, prog.anchor, GetNode("V/Deadline/Registration/Student/Classes") ) ) and len( ESPUser(request.user).getEnrolledClasses(prog, request) ) >= 1:
            raise ESPError(False), "You are only allowed to register for one class at this time.  Please come back later!"

        cobj = Class.objects.filter(id=classid)[0]
        error = cobj.cannotAdd(self.user,self.classRegInfo.enforce_max,use_cache=False)
        
        if not hasattr(self.user, "onsite_local"):
            self.user.onsite_local = False
            
        if error and not self.user.onsite_local:
            raise ESPError(False), error
        if cobj.preregister_student(self.user, self.user.onsite_local):
            cobj.update_cache_students()
            return self.goToCore(tl) # go to the core view.
        else:
            raise ESPError(False), 'According to our latest information, this class is full. Please go back and choose another class.'


    @needs_student
    @meets_deadline('/Classes/OneClass')    
    def fillslot(self, request, tl, one, two, module, extra, prog):
        """ Display the page to fill the timeslot for a program """
        from esp.cal.models import Event

        try:
            extra = int(extra)
        except:
            raise ESPError(False), 'Please use the link at the main registration page.'
        
        ts = Event.objects.filter(id=extra)
        if len(ts) < 1:
            raise Http404()

        ts = ts[0]

        prereg_url = self.program.get_learn_url + 'addclass/'
        user_grade = ESPUser(request.user).getGrade()
        
         # using .extra() to select all the category text simultaneously
        classes = [c for c in Class.objects.catalog(self.program, ts).filter(grade_min__lte=user_grade, grade_max__gte=user_grade) if not c.isFull()] 

        categories = {}

        for cls in classes:
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt}


        return render_to_response(self.baseDir()+'fillslot.html', request, (prog, tl), {'classes':    classes,
                                                                                        'one':        one,
                                                                                        'two':        two,
                                                                                        'categories': categories.values(),
                                                                                        'timeslot':   ts,
                                                                                        'prereg_url': prereg_url})
       

    # we can also ``changeslot''
    changeslot = fillslot

    @meets_deadline('/Catalog')
    def catalog(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog """
        

        # using .extra() to select all the category text simultaneously
        classes = Class.objects.catalog(self.program)

        categories = {}
        for cls in classes:
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt}
        
        return render_to_response(self.baseDir()+'catalog.html', request, (prog, tl), {'classes': classes,
                                                                                       'one':        one,
                                                                                       'two':        two,
                                                                                       'categories': categories.values()})

    @needs_student
    def class_docs(self, request, tl, one, two, module, extra, prog):
        from esp.qsdmedia.models import Media

        clsid = 0
        if request.POST.has_key('clsid'):
            clsid = request.POST['clsid']
        else:
            clsid = extra
            
        classes = Class.objects.filter(id = clsid)
        
        target_class = classes[0]

        context = {'cls': target_class, 'module': self}
	
        return render_to_response(self.baseDir()+'class_docs.html', request, (prog, tl), context)

    @needs_student
    @meets_deadline('/Classes/OneClass')    
    def clearslot(self, request, tl, one, two, module, extra, prog):
	""" Clear the specified timeslot from a student registration and go back to the same page """
        from esp.users.models import UserBit
	v_registered = request.get_node('V/Flags/Registration/Preliminary')
	
        classes = Class.objects.filter(meeting_times=extra,
                             parent_program = self.program,
                             anchor__userbit_qsc__verb = v_registered,
                             anchor__userbit_qsc__user = self.user).distinct()

        for cls in classes:
            cls.unpreregister_student(self.user)

	return self.goToCore(tl)


    def getNavBars(self):
        """ Returns a list of the dictionary to render the class catalog, if it's open """
        if super(StudentClassRegModule, self).deadline_met('/Catalog'):
            return [{ 'link': '/learn/%s/catalog' % ( self.program.getUrlBase() ),
                      'text': '%s Catalog' % ( self.program.niceSubName() ) }]
        
        else:
            return []
