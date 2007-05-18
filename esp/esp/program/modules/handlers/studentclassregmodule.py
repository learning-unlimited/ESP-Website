
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
from esp.users.models    import ESPUser, UserBit
from esp.db.models       import Q
from django.template.loader import get_template

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
            return {'classreg': ESPUser.objects.filter((Conf | Prel)).distinct()}


    def studentDesc(self):
        return {'classreg': """Students who have are enrolled in at least one class."""}
    
    def isCompleted(self):
        self.user = ESPUser(self.user)
        if self.user.getEnrolledClasses().count() == 0:
            return False
        return self.user.getEnrolledClasses().filter(parent_program = self.program).count() > 0

    def deadline_met(self):
        #tmpModule = ProgramModuleObj()
        #tmpModule.__dict__ = self.__dict__
        return super(StudentClassRegModule, self).deadline_met('/Classes')

    
    @needs_student
    def prepare(self, context={}):
	regProf = RegistrationProfile.getLastForProgram(self.user, self.program)
	timeslots = list(GetNode(self.program.anchor.full_name()+'/Templates/TimeSlots').children().order_by('id'))
	classList = regProf.preregistered_classes()

        schedule = []
        for timeslot in timeslots:
            newClasses = classList.filter(meeting_times = timeslot)
            if len(newClasses) > 0:
                schedule.append((timeslot, newClasses[0]))
            else:
                schedule.append((timeslot, None))
                
        context['timeslots'] = schedule
        
	return context

    @needs_student
    @meets_deadline('/Classes')
    def addclass(self,request, tl, one, two, module, extra, prog):
        """ Preregister a student for the specified class, then return to the studentreg page """

        if request.POST.has_key('class_id'):
            classid = request.POST['class_id']
        else:
            from esp.dblog.models import error
            raise ESPError(), "We've lost track of your chosen class's ID!  Please try again; make sure that you've clicked the \"Add Class\" button, rather than just typing in a URL."
            
        cobj = Class.objects.filter(id=classid)[0]
        error = cobj.cannotAdd(self.user,self.classRegInfo.enforce_max)
        if error and not self.user.onsite_local:
            raise ESPError(False), error
        if cobj.preregister_student(self.user, self.user.onsite_local):
            cobj.update_cache_students()
            return self.goToCore(tl) # go to the core view.
        else:
            raise ESPError(False), 'Class is full. Please go back to the catalog and choose another class.'


    @needs_student
    @meets_deadline('/Classes')    
    def fillslot(self, request, tl, one, two, module, extra, prog):
        """ Display the page to fill the timeslot for a program """


        try:
            extra = int(extra)
        except:
            raise ESPError(False), 'Please use the link at the main registration page.'
        
        ts = DataTree.objects.filter(id=extra)
        if len(ts) < 1:
            raise Http404()

        ts = ts[0]

        prereg_url = self.program.get_learn_url + 'addclass/'

        classes = Class.objects.approved().filter(parent_program = self.program, meeting_times = ts).order_by('category')

        categories = classes.values('category').distinct()
        categories = ClassCategories.objects.filter(id__in = [ x['category'] for x in categories ])


        return render_to_response(self.baseDir()+'fillslot.html', request, (prog, tl), {'classes':    classes,
                                                                                        'one':        one,
                                                                                        'two':        two,
                                                                                        'categories': categories,
                                                                                        'timeslot':   ts,
                                                                                        'prereg_url': prereg_url})
       

    # we can also ``changeslot''
    changeslot = fillslot

    @meets_deadline('/Catalog')
    def catalog(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program class catalog """
        

        classes = Class.objects.approved().filter(parent_program = self.program).order_by('category')

        categories = classes.values('category').distinct()
        categories = ClassCategories.objects.filter(id__in = [ x['category'] for x in categories ])


        return render_to_response(self.baseDir()+'catalog.html', request, (prog, tl), {'classes': classes,
                                                                                       'one':        one,
                                                                                       'two':        two,
                                                                                       'categories': categories})

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
    @meets_deadline('/Classes')    
    def clearslot(self, request, tl, one, two, module, extra, prog):
	""" Clear the specified timeslot from a student registration and go back to the same page """
        from esp.users.models import UserBit
	ts = DataTree.objects.filter(id=extra)[0]
	v_registered = GetNode('V/Flags/Registration/Preliminary')
	
	#	Get list of all pre-registration userbits
	prereg_ubs = UserBit.objects.filter(user=request.user, verb=v_registered)
	
	#	Find the userbits for classes in that timeslot and delete them.
	for ub in prereg_ubs:
            if Class.objects.filter(meeting_times=extra, anchor=ub.qsc).count() > 0:
                cobj = Class.objects.filter(anchor = ub.qsc)
                if len(cobj) > 0:
                    for cls in cobj:
                        cls.update_cache_students()
		ub.delete()



	return self.goToCore(tl)

