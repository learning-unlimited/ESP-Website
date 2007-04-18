
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.program.models import Class, Program
from esp.users.models import UserBit, ESPUser
from esp.datatree.models import DataTree
from django.utils.datastructures import MultiValueDict
from esp.cal.models              import Event
from esp.program.modules.manipulators import ClassManageManipulator
from django import forms
from django.http import HttpResponseRedirect

class AdminClass(ProgramModuleObj):
    """ This module is extremely useful for managing classes if you have them them in your program.
        Works best with student and teacher class modules, but they are not necessary.
        Options for this are available on the main manage page.
        """
    def getManageSteps(self):
        return [('Interviewed','Teacher Interviewed'),
                ('Scheduled', 'Schedule Completed'),
                ('RoomAssigned','Room Assignment Completed'),
                ('Finished', 'Finished All')]
    
    def getResources(self):
        resources = self.program.getResources()
        return [(str(x.id), x.friendly_name) for x in resources]

    def getClassSizes(self):
        min_size, max_size, class_size_step = (0, 200, 10)
        if self.classRegInfo.class_min_size:
            min_size = self.classRegInfo.class_min_size
            
        if self.classRegInfo.class_max_size:
            max_size = self.classRegInfo.class_max_size
            
        if self.classRegInfo.class_size_step:
            class_size_step = self.classRegInfo.class_size_step

        return range(min_size, max_size+1, class_size_step)

    def getTimes(self):
        times = self.program.getTimeSlots()
        return [(str(x.id),x.friendly_name) for x in times]

    def timeslotNumClasses(self):
        timeslots = self.program.getTimeSlots()
        clsTimeSlots = []
        for timeslot in timeslots:
            curTimeslot = {'slotname': timeslot.friendly_name}
            
            curclasses = Class.objects.filter(parent_program = self.program,
                                              meeting_times  = timeslot)

            curTimeslot['classcount'] = curclasses.count()

            clsTimeSlots.append(curTimeslot)
        return clsTimeSlots


    def getClassGrades(self):
        min_grade, max_grade = (6, 12)
        if self.program.grade_min:
            min_grade = self.program.grade_min
        if self.program.grade_max:
            max_grade = self.program.grade_max

        return range(min_grade, max_grade+1)

    def getClasses(self):
        return self.user.getEditable(Class).filter(parent_program = self.program)
        
    def prepare(self, context={}):
        classes = self.getClasses()
        context['noclasses'] = (len(classes) == 0)
        context['classes']   = classes
        return context

    def getClass(self, request, extra):
        found = False
        if not found and extra is not None and len(extra.strip()) > 0:
            try:
                clsid = int(extra)
            finally:
                cls, found = self.getClassFromId(extra)
                if found:
                    return (cls, True)
                elif cls is not False:
                    return (cls, False)
                

        if not found and request.POST.has_key('clsid'):
            try:
                clsid = int(request.POST['clsid'])
            finally:
                cls, found = self.getClassFromId(extra)
                if found:
                    return (cls, True)
                elif cls is not False:
                    return (cls, False)

        if not found and request.GET.has_key('clsid'):
            try:
                clsid = int(request.GET['clsid'])
            finally:
                cls, found = self.getClassFromId(extra)
                if found:
                    return (cls, True)
                elif cls is not False:
                    return (cls, False)

                
        return (render_to_response(self.baseDir()+'cannotfindclass.html', request, (prog, tl), {}), False)

    @needs_admin
    def changeoption(self, request,tl, one, two, module, extra, prog):
        from esp.datatree.models import GetNode
        cls, found = self.getClass(request,extra)
        if not found:
            return cls
        verb_start = 'V/Flags/Class/'
        
        if request.GET.has_key('step'):
            verb = GetNode(verb_start+request.GET['step'])
            if UserBit.UserHasPerms(user = None, verb = verb, qsc = cls.anchor):
                UserBit.objects.filter(user__isnull = True, qsc = cls.anchor, verb = verb).delete()
            else:
                UserBit.objects.get_or_create(user = None, qsc = cls.anchor, verb = verb, recursive = False)

        return self.goToCore(tl)
        
                
    @needs_admin
    def manageclass(self, request, tl, one, two, module, extra, prog):
        from esp.datatree.models import GetNode
        cls, found = self.getClass(request,extra)
        if not found:
            return cls
        context = {'class': cls,
                   'module': self}

        manipulator = ClassManageManipulator(cls, self)
        new_data = {}
        if request.method == 'POST':
            new_data = request.POST.copy()

            errors = manipulator.get_validation_errors(new_data)
            
            if not errors:
                verb_start = 'V/Flags/Class/'
                manipulator.do_html2python(new_data)
                progress = request.POST.getlist('manage_progress')
                for step in ['Interviewed','Finished','Scheduled','RoomAssigned']:
                    
                    if step in progress:

                        UserBit.objects.get_or_create(user      = None,
                                                      qsc       = cls.anchor,
                                                      verb      = GetNode(verb_start+step),
                                                      recursive = False)
                    else:
                        [ x.delete() for x in
                          UserBit.objects.filter(user__isnull = True,
                                                 qsc          = cls.anchor,
                                                 verb         = GetNode(verb_start+step),
                                                 recursive    = False) ]

                cls.meeting_times.clear()
                cls.directors_notes = new_data['directors_notes']
                cls.message_for_directors = new_data['message_for_directors']                
                for meeting_time in request.POST.getlist('meeting_times'):
                    cls.meeting_times.add(DataTree.objects.get(id = str(meeting_time)))
                cls.save()
                rooms = request.POST.getlist('room')
                cls.clearRooms()
                for room in rooms:
                    if len(room.strip()) > 0:
                        cls.assignClassRoom(DataTree.objects.get(id = room))

                cls.update_cache()
                
                return self.goToCore(tl)
        else:
            new_data['meeting_times']   = [x.id for x in cls.meeting_times.all()]
            new_data['directors_notes'] = cls.directors_notes
            new_data['message_for_directors'] = cls.message_for_directors            
            new_data['resources'] = [ resource.id for resource in cls.resources.all() ]

            steps = []
            if cls.manage_finished():
                steps += ['Finished']
            if cls.manage_scheduled():
                steps += ['Scheduled']
            if cls.manage_roomassigned():
                steps += ['RoomAssigned']
            if cls.teacher_interviewed():
                steps.append('Interviewed')
                
            new_data['manage_progress'] = steps

            
            classrooms = cls.classrooms()
            if len(classrooms) > 0:
                new_data['room']      = cls.classrooms()[0].id
            errors = {}

        form = forms.FormWrapper(manipulator, new_data, errors)
        context['form'] = form

        return render_to_response(self.baseDir()+'manageclass.html',
                                  request,
                                  (prog, tl),
                                  context)

                                  
        
        



    @needs_admin
    def approveclass(self, request, tl, one, two, module, extra, prog):
        cls, found = self.getClass(request, extra)
        if not found:
            return cls
        cls.accept()
        if request.GET.has_key('redirect'):
            return HttpResponseRedirect(request.GET['redirect'])
        return self.goToCore(tl)        

    @needs_admin
    def rejectclass(self, request, tl, one, two, module, extra, prog):
        cls, found = self.getClass(request, extra)
        if not found:
            return cls
        cls.reject()
        if request.GET.has_key('redirect'):
            return HttpResponseRedirect(request.GET['redirect'])
        return self.goToCore(tl)

    @needs_admin
    def proposeclass(self, request, tl, one, two, module, extra, prog):
        cls, found = self.getClass(request, extra)
        if not found:
            return cls
        cls.propose()
        if request.GET.has_key('redirect'):
            return HttpResponseRedirect(request.GET['redirect'])
        return self.goToCore(tl)
    
    @needs_admin
    def main(self, request, tl, one, two, module, extra, prog):
        """ Display a teacher eg page """
        context = {}
        modules = self.program.getModules(self.user, 'manage')
        
        for module in modules:
            context = module.prepare(context)

                    
        context['modules'] = modules
        context['one'] = one
        context['two'] = two

        return render_to_response(self.baseDir()+'mainpage.html', request, (prog, tl), context)

    
 
    @needs_admin
    def deleteclass(self, request, tl, one, two, module, extra, prog):
        classes = Class.objects.filter(id = extra)
        if len(classes) != 1 or not self.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, (prog, tl),{})
        cls = classes[0]
        cls.delete(True)
        return self.goToCore(tl)

    @needs_admin
    def coteachers(self, request, tl, one, two, module, extra, prog):
        from esp.users.models import ESPUser 
        if not request.POST.has_key('clsid'):
            return self.goToCore(tl) # just fails.

        if extra == 'nojs':
            ajax = False
        else:
            ajax = True
            
        classes = Class.objects.filter(id = request.POST['clsid'])
        if len(classes) != 1 or not self.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, (prog, tl),{})

        cls = classes[0]

        # set txtTeachers and coteachers....
        if not request.POST.has_key('coteachers'):
            coteachers = cls.teachers()
            coteachers = [ ESPUser(user) for user in coteachers
                           if user.id != self.user.id           ]
            
            txtTeachers = ",".join([str(user.id) for user in coteachers ])
            
        else:
            txtTeachers = request.POST['coteachers']
            coteachers = txtTeachers.split(',')
            coteachers = [ x for x in coteachers if x != '' ]
            coteachers = [ ESPUser(ESPUser.objects.get(id=userid))
                           for userid in coteachers                ]

        op = ''
        if request.POST.has_key('op'):
            op = request.POST['op']

        conflictingusers = []
        error = False
        
        if op == 'add':

            if len(request.POST['teacher_selected'].strip()) == 0:
                error = 'Error - Please click on the name when it drops down.'

            elif (request.POST['teacher_selected'] == str(self.user.id)):
                error = 'Error - You cannot select yourself as a coteacher!'
            elif request.POST['teacher_selected'] in txtTeachers.split(','):
                error = 'Error - You already added this teacher as a coteacher!'

            if error:
                return render_to_response(self.baseDir()+'coteachers.html', request, (prog, tl),{'class':cls,
                                                                                                 'ajax':ajax,
                                                                                                 'txtTeachers': txtTeachers,
                                                                                                 'coteachers':  coteachers,
                                                                                                 'error': error})
            
            # add schedule conflict checking here...
            teacher = ESPUser.objects.get(id = request.POST['teacher_selected'])

            if cls.conflicts(teacher):
                conflictingusers.append(teacher.first_name+' '+teacher.last_name)
            else:    
                coteachers.append(teacher)
                txtTeachers = ",".join([str(coteacher.id) for coteacher in coteachers ])
            
        elif op == 'del':
            ids = request.POST.getlist('delete_coteachers')
            newcoteachers = []
            for coteacher in coteachers:
                if str(coteacher.id) not in ids:
                    newcoteachers.append(coteacher)

            coteachers = newcoteachers
            txtTeachers = ",".join([str(coteacher.id) for coteacher in coteachers ])
                         

        elif op == 'save':
            #            if
            for teacher in coteachers:
                if cls.conflicts(teacher):
                    conflictingusers.append(teacher.first_name+' '+teacher.last_name)
            if len(conflictingusers) == 0:
                for teacher in cls.teachers():
                    cls.removeTeacher(teacher)
                    cls.removeAdmin(teacher)

                # add self back...
                cls.makeTeacher(self.user)
                cls.makeAdmin(self.user, self.classRegInfo.teacher_class_noedit)

                # add bits for all new (and old) coteachers
                for teacher in coteachers:
                    cls.makeTeacher(teacher)
                    cls.makeAdmin(teacher, self.classRegInfo.teacher_class_noedit)                    
                
                return self.goToCore(tl)


        
        return render_to_response(self.baseDir()+'coteachers.html', request, (prog, tl),{'class':cls,
                                                                                         'ajax':ajax,
                                                                                         'txtTeachers': txtTeachers,
                                                                                         'coteachers':  coteachers,
                                                                                         'conflicts':   conflictingusers})
    @needs_admin
    def editclass(self, request, tl, one, two, module, extra, prog):
        classes = Class.objects.filter(id = extra)
        if len(classes) != 1 or not self.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, (prog, tl),{})
        cls = classes[0]

        return self.makeaclass(request, tl, one, two, module, extra, prog, cls)

    @needs_admin
    def makeaclass(self, request, tl, one, two, module, extra, prog, newclass = None):
        
        new_data = MultiValueDict()
        context = {'module': self}
        new_data['grade_max'] = str(self.getClassGrades()[-1:][0])
        new_data['class_size_max']  = str(self.getClassSizes()[-1:][0])
        
        manipulator = manipulators.TeacherClassRegManipulator(self)

        if request.method == 'POST' and request.POST.has_key('class_reg_page'):
            if not self.deadline_met():
                return self.goToCore();
            
            new_data = request.POST.copy()
            #assert False, new_data            
            errors = manipulator.get_validation_errors(new_data)
            if not errors:
                manipulator.do_html2python(new_data)

                if newclass is None:
                    newclass = Class()

                if len(new_data['message_for_directors'].strip()) > 0 and \
                       new_data['message_for_directors'] != newclass.message_for_directors and \
                       self.classRegInfo.director_email:

                    send_mail('['+self.program.anchor.parent.friendly_name+"] Directors' Comments for Teacher Reg", \
                              """ Directors\' comments below:\nClass Title: %s\n\n %s\n\n>>>>>>>>>>>EOM""" % \
                              (new_data['title'], new_data['message_for_directors']) , \
                              ('%s <%s>' % (self.user.first_name + ' ' + self.user.last_name, self.user.email,)), \
                              [self.classRegInfo.director_email], True)


                for k, v in new_data.items():
                    if k != 'resources' and k != 'viable_times':
                        newclass.__dict__[k] = v

                if new_data['duration'] == '':
                    newclass.duration = 0.0
                else:
                    newclass.duration = float(new_data['duration'])
                    
                # datatree maintenance
                newclass.parent_program = self.program
                newclass.category = ClassCategories.objects.get(id=new_data['category'])
                newclass.anchor = self.program.anchor.tree_create(['DummyClass'])
                newclass.anchor.save()
                newclass.enrollment = 0
                newclass.save()
                newclass.anchor.delete()
                
                nodestring = newclass.category.category[:1].upper() + str(newclass.id)
                newclass.anchor = self.program.classes_node().tree_create([nodestring])
                newclass.anchor.friendly_name = newclass.title
                newclass.anchor.save()
                newclass.save()


                # ensure multiselect fields are set
                newclass.viable_times.clear()
                for block in request.POST.getlist('viable_times'):
                    tmpQsc = DataTree.objects.get(id = int(block))
                    newclass.viable_times.add(tmpQsc)


                newclass.resources.clear()
                for resource in request.POST.getlist('resources'):
                    tmpQsc = DataTree.objects.get(id = int(resource))
                    newclass.resources.add(tmpQsc)

                # add userbits
                newclass.makeTeacher(self.user)
                newclass.makeAdmin(self.user, self.classRegInfo.teacher_class_noedit)

                return self.goToCore(tl)
                            
        else:
            errors = {}
            if newclass is not None:
                new_data = newclass.__dict__
                new_data['category'] = newclass.category.id
                new_data['resources'] = [ resource.id for resource in newclass.resources.all() ]
                new_data['viable_times'] = [ event.id for event in newclass.viable_times.all() ]
                new_data['title'] = newclass.anchor.friendly_name
                new_data['url']   = newclass.anchor.name
                context['class'] = newclass

        #assert False, new_data
        context['one'] = one
        context['two'] = two
        if newclass is None:
            context['addoredit'] = 'Add'
        else:
            context['addoredit'] = 'Edit'

        #        assert False, new_data
        context['form'] = forms.FormWrapper(manipulator, new_data, errors)


        if len(self.getDurations()) < 2:
            context['durations'] = False
        else:
            context['durations'] = True
            
        return render_to_response(self.baseDir() + 'classedit.html', request, (prog, tl), context)


    @needs_admin
    def teacherlookup(self, request, tl, one, two, module, extra, prog, newclass = None):
        limit = 10
        from esp.web.views.json import JsonResponse
        from esp.users.models import UserBit
        from esp.db.models import Q

        # Initialize anchors for identifying teachers
        q = GetNode( 'Q' )
        v = GetNode( 'V/Flags/UserRole/Teacher' )

        # Select teachers
        queryset = UserBit.bits_get_users(q, v)

        # Search for teachers with names that start with search string
        if not request.GET.has_key('q'):
            return self.goToCore()
        
        startswith = request.GET['q']
        parts = [x.strip() for x in startswith.split(',')]
        Q_name = Q(user__last_name__istartswith=parts[0])
        if len(parts) > 1:
            Q_name = Q_name & Q(user__first_name__istartswith=parts[1])

        # Isolate user objects
        queryset = queryset.filter(Q_name)[:(limit*10)]
        users = [ub.user for ub in queryset]
        user_dict = {}
        for user in users:
            user_dict[user.id] = user
        users = user_dict.values()

        # Construct combo-box items
        obj_list = [[user.last_name + ', ' + user.first_name + ' ('+user.username+')', user.id] for user in users]

        # Operation Complete!
        return JsonResponse(obj_list)

