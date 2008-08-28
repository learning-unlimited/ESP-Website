
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.modules import module_ext

from esp.program.models import ClassSubject, ClassSection, Program, ProgramCheckItem
from esp.users.models import UserBit, ESPUser, User
from esp.datatree.models import DataTree
from esp.cal.models              import Event

from esp.web.util        import render_to_response
from esp.program.modules.forms.management import ClassManageForm, SectionManageForm

from django import oldforms
from django import forms
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.datastructures import MultiValueDict
from django.contrib.auth.decorators import login_required
from esp.middleware import ESPError
from esp.db.models import Q

""" Module in the middle of a rewrite. -Michael """

class AdminClass(ProgramModuleObj):
    doc = """ This module is extremely useful for managing classes if you have them them in your program.
        Works best with student and teacher class modules, but they are not necessary.
        Options for this are available on the main manage page.
        """

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Manage Classes",
            "module_type": "manage",
            "seq": 1,
            "main_call": "listclasses"
            }
        
    form_choice_types = ['status', 'room', 'progress', 'resources', 'times', 'min_grade', 'max_grade']
    def getFormChoices(self, field_str):
        """ A more compact function for zipping up the options available on class
        management forms. """
        
        if field_str == 'status':
            return ((-20, 'Cancelled'), (-10, 'Rejected'), (0, 'Unreviewed'), (10, 'Accepted'))
        if field_str == 'room':
            room_choices = [(c.name, c.name) for c in self.program.groupedClassrooms()]
            return [(None, 'Unassigned')] + room_choices
        if field_str == 'progress':
            return ((str(x.id),x.title) for x in self.program.checkitems.all())
        if field_str == 'resources':
            resources = self.program.getFloatingResources()
            return ((x.name, x.name) for x in resources)
        if field_str == 'times':
            times = self.program.getTimeSlots()
            return ((str(x.id),x.short_description) for x in times)
        if field_str == 'min_grade' or field_str == 'max_grade':
            min_grade, max_grade = (7, 12)
            if self.program.grade_min:
                min_grade = self.program.grade_min
            if self.program.grade_max:
                max_grade = self.program.grade_max
            return ((i, str(i)) for i in range(min_grade, max_grade + 1))

    def timeslot_counts(self):
        timeslots = self.program.getTimeSlots()
        clsTimeSlots = []
        for timeslot in timeslots:
            curTimeslot = {'slotname': timeslot.short_time()}
            section_list = self.program.sections().filter(meeting_times=timeslot)
            curTimeslot['classcount'] = section_list.count()
            clsTimeSlots.append(curTimeslot)
        return clsTimeSlots

    def getClasses(self):
        return self.user.getEditable(ClassSubject).filter(parent_program = self.program)
        
    def prepare(self, context=None):
        if context is None: context = {}
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
                cls, found = self.getClassFromId(clsid)
                if found:
                    return (cls, True)
                elif cls is not False:
                    return (cls, False)
                

        if not found and request.POST.has_key('clsid'):
            try:
                clsid = int(request.POST['clsid'])
            finally:
                cls, found = self.getClassFromId(clsid)
                if found:
                    return (cls, True)
                elif cls is not False:
                    return (cls, False)

        if not found and request.GET.has_key('clsid'):
            try:
                clsid = int(request.GET['clsid'])
            finally:
                cls, found = self.getClassFromId(clsid)
                if found:
                    return (cls, True)
                elif cls is not False:
                    return (cls, False)

                
        return (render_to_response(self.baseDir()+'cannotfindclass.html', {}), False)

    @needs_admin
    def attendees(self, request, tl, one, two, module, extra, prog):
        """ Mark students as having attended the program, or as having registered for the specified class """
        saved_record = False
        
        if request.method == 'POST':
            if not( request.POST.has_key('class_id') and request.POST.has_key('ids_to_enter') ):
                raise ESPError(), "Error: The server lost track of your data!  Please go back to the main page of this feature and try entering it again."

            usernames = []
            ids = []

            for id in [ x for x in request.POST['ids_to_enter'].split('\n') if x.strip() != '' ]:
                try: # We're going to accept both usernames and user ID's.
                     # Assume that valid integers are user ID's
                     # and things that aren't valid integers are usernames.
                    if id[0] == '0':
                        id_trimmed = id.strip()[:-1]
                    else:
                        id_trimmed = id
                    
                    id_val = int(id_trimmed)
                    ids.append(id_val)
                except ValueError:
                    usernames.append( id.strip() )
                    
            Q_Users = Q()
            if usernames != []:
                Q_Users |= Q(username__in = usernames)

            if ids != []:
                Q_Users |= Q(id__in = ids)
                    
            users = User.objects.filter( Q_Users )

            if request.POST['class_id'] == 'program':
                already_registered_users = prog.students()['attended']
            else:
                cls = ClassSection.objects.get(id = request.POST['class_id'])
                already_registered_users = cls.students()

            already_registered_ids = [ i.id for i in already_registered_users ]
                                               
            new_attendees = User.objects.filter( Q_Users )
            if already_registered_ids != []:
                new_attendees = new_attendees.exclude( id__in = already_registered_ids )
            new_attendees = new_attendees.distinct()

            no_longer_attending = User.objects.filter( id__in = already_registered_ids )
            if ids != [] or usernames != []:
                no_longer_attending = no_longer_attending.exclude( Q_Users )
            no_longer_attending = no_longer_attending.distinct()

            if request.POST['class_id'] == 'program':
                for stu in no_longer_attending:
                    prog.cancelStudentRegConfirmation(stu)
                for stu in new_attendees:
                    prog.confirmStudentReg(stu)
            else:
                for stu in no_longer_attending:
                    cls.unpreregister_student(stu)
                for stu in new_attendees:
                    cls.preregister_student(stu, overridefull=True)
                    
            saved_record = True
        else:
            if request.GET.has_key('class_id'):
                if request.GET['class_id'] == 'program':
                    is_program = True
                    registered_students = prog.students()['attended']
                else:
                    is_program = False
                    cls = ClassSection.objects.get(id = request.GET['class_id'])
                    registered_students = cls.students()

                context = { 'is_program': is_program,
                            'prog': prog,
                            'cls': cls,
                            'registered_students': registered_students,
                            'class_id': request.GET['class_id'] }
                    
                return render_to_response(self.baseDir()+'attendees_enter_users.html', request, (prog, tl), context)

        return render_to_response(self.baseDir()+'attendees_selectclass.html', request, (prog, tl), { 'saved_record': saved_record, 'prog': prog })
        
    @needs_admin
    def deletesection(self, request, tl, one, two, module, extra, prog):
        """ A little function to remove the section specified in POST. """
        if request.method == 'POST':
            if request.POST.has_key('sure') and request.POST['sure'] == 'True':
                try:
                    s = ClassSection.objects.get(id=int(request.GET['sec_id']))
                    s.delete()
                    return HttpResponseRedirect('/manage/%s/%s/manageclass/%s' % (one, two, extra))
                except:
                    raise ESPError(False), 'Unable to delete a section.  The section requested was: %s' % request.GET['sec_id']
        else:
            section_id = int(request.GET['sec_id'])
            section = ClassSection.objects.get(id=section_id)
            context = {'sec': section, 'module': self}
            
            return render_to_response(self.baseDir()+'delete_confirm.html', request, (prog, tl), context)
                
    @needs_admin
    def addsection(self, request, tl, one, two, module, extra, prog):
        """ A little function to add a section to the class specified in POST. """
        cls, found = self.getClass(request,extra)
        cls.add_section()
                    
        return HttpResponseRedirect('/manage/%s/%s/manageclass/%s' % (one, two, extra))

    @aux_call
    @needs_admin
    def manageclass(self, request, tl, one, two, module, extra, prog):
        cls, found = self.getClass(request,extra)
        sections = cls.sections.all()
        if not found:
            return ESPError(False), 'Unable to find the requested class.'
        context = {}
        
        cls_form = ClassManageForm(self, subject=cls)
        sec_forms = [SectionManageForm(self, section=sec, prefix='sec'+str(sec.index())) for sec in sections]
        
        if request.method == 'POST':
            data = request.POST.copy()
            #   assert False, data
            
            cls_form.data = data
            cls_form.is_bound = True
            valid = cls_form.is_valid()
            for sf in sec_forms:
                sf.data = data
                sf.is_bound = True
                valid = (valid and sf.is_valid())
            
            if valid:
                cls_alter = ClassSubject.objects.get(id=cls_form.cleaned_data['clsid'])
                cls_form.save_data(cls_alter)
                for sf in sec_forms:
                    sec_alter = ClassSection.objects.get(id=sf.cleaned_data['secid'])
                    sf.save_data(sec_alter)
                return HttpResponseRedirect('/manage/%s/%s/dashboard' % (one, two))
        
        context['class'] = cls
        context['sections'] = sections
        context['cls_form'] = cls_form
        context['sec_forms'] = sec_forms
        context['program'] = self.program
        context['module'] = self
        
        return render_to_response(self.baseDir()+'manageclass.html', request, (prog, tl), context)

    @aux_call
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

    @aux_call
    @needs_admin
    def proposeclass(self, request, tl, one, two, module, extra, prog):
        cls, found = self.getClass(request, extra)
        if not found:
            return cls
        cls.propose()
        if request.GET.has_key('redirect'):
            return HttpResponseRedirect(request.GET['redirect'])
        return self.goToCore(tl)

    def change_checkmark(self, class_id, check_id):
        cls = ClassSubject.objects.get(id = class_id)
        check = ProgramCheckItem.objects.get(id = check_id)
    
        if len(cls.checklist_progress.filter(id = check_id).values('id')[:1]) > 0:
            cls.checklist_progress.remove(check)
            return False
        else:
            cls.checklist_progress.add(check)
            return True

    @aux_call
    @needs_admin
    def alter_checkmark(self, request, *args, **kwargs):
        """
        Change the status of a check mark for a given class.
        """
        class_id = request.POST.get('class_id','')
        check_id = request.POST['check_id']

        result = self.change_checkmark(class_id, check_id)

        if result:
            return HttpResponse('On');
        else:
            return HttpResponse('Off');

    @aux_call
    @needs_admin
    def changeoption(self, request,tl,one,two,module,extra,prog):
        check_id = request.GET['step']
        class_id = extra

        self.change_checkmark(class_id, check_id)

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

    @aux_call
    @needs_admin
    def deleteclass(self, request, tl, one, two, module, extra, prog):
        classes = ClassSubject.objects.filter(id = extra)
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
            
        classes = ClassSubject.objects.filter(id = request.POST['clsid'])
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
            coteachers = [ ESPUser(User.objects.get(id=userid))
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
            teacher = User.objects.get(id = request.POST['teacher_selected'])

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
                cls.makeAdmin(self.user, self.teacher_class_noedit)

                # add bits for all new (and old) coteachers
                for teacher in coteachers:
                    cls.makeTeacher(teacher)
                    cls.makeAdmin(teacher, self.teacher_class_noedit)                    
                
                return self.goToCore(tl)


        
        return render_to_response(self.baseDir()+'coteachers.html', request, (prog, tl),{'class':cls,
                                                                                         'ajax':ajax,
                                                                                         'txtTeachers': txtTeachers,
                                                                                         'coteachers':  coteachers,
                                                                                         'conflicts':   conflictingusers})

    @aux_call
    @needs_admin
    def editclass(self, request, tl, one, two, module, extra, prog):
        """ Hand over to the teacher class reg module so we only have this code in one place. """
        from esp.program.modules.handlers.teacherclassregmodule import TeacherClassRegModule
        
        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) != 1 or not self.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, (prog, tl),{})
        cls = classes[0]

        #   May have to change so that the user is redirected to the dashboard after saving.
        #   It might do this already.
        return TeacherClassRegModule(self).makeaclass(request, tl, one, two, module, extra, prog, cls)

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

