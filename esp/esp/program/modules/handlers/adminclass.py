
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.modules import module_ext
from esp.program.controllers.consistency import ConsistencyChecker
from esp.program.modules.handlers.teacherclassregmodule import TeacherClassRegModule

from esp.program.models import ClassSubject, ClassSection, Program, ProgramCheckItem, ClassFlagType
from esp.users.models import ESPUser, User
from esp.datatree.models import *
from esp.cal.models              import Event

from esp.web.util        import render_to_response
from esp.program.modules.forms.management import ClassManageForm, SectionManageForm, ClassCancellationForm, SectionCancellationForm

from django import forms
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.datastructures import MultiValueDict
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from esp.middleware import ESPError
from django.db.models.query import Q
from esp.program.controllers.classreg import ClassCreationController

""" Module in the middle of a rewrite. -Michael """

class AdminClass(ProgramModuleObj):
    doc = """ This module is extremely useful for managing classes if you have them them in your program.
        Works best with student and teacher class modules, but they are not necessary.
        Options for this are available on the main manage page.
        """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Class Management for Admin",
            "link_title": "Manage Classes",
            "module_type": "manage",
            "inline_template": "listclasses.html",
            "seq": 1,
            }
        
    form_choice_types = ['status', 'reg_status', 'room', 'progress', 'resources', 'times', 'min_grade', 'max_grade']
    def getFormChoices(self, field_str):
        """ A more compact function for zipping up the options available on class
        management forms. """
        
        if field_str == 'status':
            return ((-20, 'Cancelled'), (-10, 'Rejected'), (0, 'Unreviewed'), (5, 'Accepted but hidden'), (10, 'Accepted'))
        if field_str == 'reg_status':
            return (('', 'Leave unchanged'), (0, 'Open'), (10, 'Closed'))
        if field_str == 'room':
            room_choices = list(self.program.getClassrooms().values_list('name','name').order_by('name').distinct())
            return [(None, 'Unassigned')] + room_choices
        if field_str == 'progress':
            return self.program.checkitems.all().values_list('id', 'title')
        if field_str == 'resources':
            resources = self.program.getFloatingResources()
            return ((x.name, x.name) for x in resources)
        if field_str == 'times':
            return self.program.getTimeSlots().values_list('id', 'short_description')
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
        return ClassSubject.objects.catalog(self.program, force_all=True, order_args_override=['id'])
        
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

    @aux_call
    @needs_admin
    def reviewClass(self, request, tl, one, two, module, extra, prog):
        """ Set the review status of a class """
        if request.method == 'POST':
            if not (request.POST.has_key('class_id') and request.POST.has_key('review_status')):
                raise ESPError("Error: missing data on request")

            class_id = request.POST['class_id']
            try:
                class_subject = ClassSubject.objects.get(pk=class_id)
            except MultipleObjectsReturned:
                raise ESPError("Error: multiple classes selected")
            except DoesNotExist:
                raise ESPError("Error: no classes found with id "+str(class_id))

            review_status = request.POST['review_status']

            if review_status == 'ACCEPT':
                # We can't just do class_subject.accept() since this only
                # accepts sections that were previously unreviewed
                for sec in class_subject.sections.all():
                    sec.status = 10
                    sec.save()
                class_subject.accept()
            elif review_status == 'UNREVIEW':
                class_subject.status = 0
                for sec in class_subject.sections.all():
                    sec.status = 0
                    sec.save()
            elif review_status == 'REJECT':
                class_subject.reject()
            else:
                raise ESPError("Error: invalid review status")
            class_subject.save()

        return HttpResponse('')

    @aux_call
    @needs_admin
    def attendees(self, request, tl, one, two, module, extra, prog):
        """ Mark students as having attended the program, or as having registered for the specified class """
        saved_record = False
        
        if request.method == 'POST':
            if not( request.POST.has_key('class_id') and request.POST.has_key('ids_to_enter') ):
                raise ESPError("Error: The server lost track of your data!  Please go back to the main page of this feature and try entering it again.")

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
                    
            Q_Users = Q(id=-1) # in case usernames and ids are both empty
            if usernames:
                Q_Users |= Q(username__in = usernames)

            if ids:
                Q_Users |= Q(id__in = ids)
                    
            users = ESPUser.objects.filter( Q_Users )

            if request.POST['class_id'] == 'program':
                already_registered_users = prog.students()['attended']
            else:
                cls = ClassSection.objects.get(id = request.POST['class_id'])
                already_registered_users = cls.students()

            already_registered_ids = [ i.id for i in already_registered_users ]
                                               
            new_attendees = ESPUser.objects.filter( Q_Users )
            if already_registered_ids != []:
                new_attendees = new_attendees.exclude( id__in = already_registered_ids )
            new_attendees = new_attendees.distinct()

            no_longer_attending = ESPUser.objects.filter( id__in = already_registered_ids )
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
                    
                return render_to_response(self.baseDir()+'attendees_enter_users.html', request, context)

        return render_to_response(self.baseDir()+'attendees_selectclass.html', request, { 'saved_record': saved_record, 'prog': prog })
        
    @aux_call
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
                    raise ESPError('Unable to delete a section.  The section requested was: %s' % request.GET['sec_id'], log=False)
        else:
            section_id = int(request.GET['sec_id'])
            section = ClassSection.objects.get(id=section_id)
            context = {'sec': section, 'module': self}
            
            return render_to_response(self.baseDir()+'delete_confirm.html', request, context)
                
    @aux_call
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
        sections = cls.sections.all().order_by('id')
        if not found:
            return ESPError('Unable to find the requested class.', log=False)
        context = {}
        
        if cls.isCancelled():
            cls_cancel_form = None
        else:
            cls_cancel_form = ClassCancellationForm(subject=cls)
        sec_cancel_forms = []
        for sec in sections:
            if sec.isCancelled():
                sec_cancel_forms.append(None)
            else:
                sec_cancel_forms.append(SectionCancellationForm(section=sec, prefix='sec'+str(sec.index())))
        
        action = request.GET.get('action', None)
        
        if request.method == 'POST':
            if action == 'cancel_cls':
                cls_cancel_form.data = request.POST
                cls_cancel_form.is_bound = True
                if cls_cancel_form.is_valid():
                    #   Call the Class{Subject,Section}.cancel() method to e-mail and remove students, etc.
                    cls_cancel_form.cleaned_data['target'].cancel(email_students=True, include_lottery_students=cls_cancel_form.cleaned_data['email_lottery_students'], explanation=cls_cancel_form.cleaned_data['explanation'], unschedule=cls_cancel_form.cleaned_data['unschedule'])
                    cls_cancel_form = None
            else:
                j = 0
                for i in [sec.index() for sec in sections]:
                    if action == ('cancel_sec_%d' % i):
                        sec_cancel_forms[j].data = request.POST
                        sec_cancel_forms[j].is_bound = True
                        if sec_cancel_forms[j].is_valid():
                            sec_cancel_forms[j].cleaned_data['target'].cancel(email_students=True, include_lottery_students=sec_cancel_forms[j].cleaned_data['email_lottery_students'], explanation=sec_cancel_forms[j].cleaned_data['explanation'], unschedule=sec_cancel_forms[j].cleaned_data['unschedule'])
                            sec_cancel_forms[j] = None
                    j += 1
        
        cls_form = ClassManageForm(self, subject=cls)
        sec_forms = [SectionManageForm(self, section=sec, prefix='sec'+str(sec.index())) for sec in cls.sections.all().order_by('id')]

        if request.method == 'POST' and action == 'modify':
            cls_form.data = request.POST
            cls_form.is_bound = True
            valid = cls_form.is_valid()
            for sf in sec_forms:
                sf.data = request.POST
                sf.is_bound = True
                valid = (valid and sf.is_valid())
            
            if valid:
                # Leave a loophole:  You can set a class to "Unreviewed" (ie., status = 0),
                # then cancel it, and it won't kick all the students out
                cls_alter = ClassSubject.objects.get(id=cls_form.cleaned_data['clsid'])
                new_status = int(cls_form.cleaned_data['status'])
                should_cancel_sections = (int(cls_alter.status) > 0 and new_status < 0)
                
                for sf in sec_forms:
                    sec_alter = ClassSection.objects.get(id=sf.cleaned_data['secid'])
                    orig_sec_status = sec_alter.status
                    sf.save_data(sec_alter)
                    
                    # If the parent class was canceled, cancel the sections
                    if should_cancel_sections and int(sec_alter.status) > 0:
                        sec_alter.status = new_status
                        sec_alter.save()

                    # Kick all the students out of a class if it was rejected
                    if int(sec_alter.status) < 0 and int(orig_sec_status) > 0:
                        for student in sec_alter.students():
                            sec_alter.unpreregister_student(student)
                
                #   Save class info after section info so that cls_form.save_data()
                #   can override section information if it's supposed to.
                #   This is needed for accepting/rejecting the sections of a 
                #   class when the sections are unreviewed.
                cls_form.save_data(cls_alter)

                return HttpResponseRedirect(request.get_full_path())
            
        consistency_checker = ConsistencyChecker(self.program)
        context['errors'] = []
        for teacher in cls.get_teachers():
            context['errors'] += consistency_checker.check_teacher_conflict(teacher)
        for section in sections:
            context['errors'] += consistency_checker.check_expected_duration(section)
            context['errors'] += consistency_checker.check_resource_consistency(section)

        if self.program.program_modules.filter(handler='ClassFlagModule').exists():
            context['show_flags'] = True
            context['flag_types'] = ClassFlagType.get_flag_types(self.program)
            
        context['class'] = cls
        context['sections'] = sections
        context['cls_form'] = cls_form
        context['sec_forms'] = sec_forms
        context['cls_cancel_form'] = cls_cancel_form
        context['sec_cancel_forms'] = sec_cancel_forms
        context['module'] = self
        
        return render_to_response(self.baseDir()+'manageclass.html', request, context)

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

    @aux_call
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
        modules = self.program.getModules(request.user, 'manage')
        
        for module in modules:
            context = module.prepare(context)

                    
        context['modules'] = modules
        context['one'] = one
        context['two'] = two

        return render_to_response(self.baseDir()+'mainpage.html', request, context)

    @aux_call
    @needs_admin
    def deleteclass(self, request, tl, one, two, module, extra, prog):
        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        cls = classes[0]

        cls.delete(True)
        return self.goToCore(tl)

    @aux_call
    @needs_admin
    def coteachers(self, request, tl, one, two, module, extra, prog):
        from esp.users.models import ESPUser 
        
        #   Allow submitting class ID via either GET or POST.
        if request.GET.has_key('clsid'):
            clsid = request.GET['clsid']
        elif request.POST.has_key('clsid'):
            clsid = request.POST['clsid']
        else:
            return self.goToCore(tl) # just fails.

        if extra == 'nojs':
            ajax = False
        else:
            ajax = True
            
        classes = ClassSubject.objects.filter(id = clsid)
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})

        cls = classes[0]

        # set txtTeachers and coteachers....
        if not request.POST.has_key('coteachers'):
            coteachers = cls.get_teachers()
            coteachers = [ ESPUser(user) for user in coteachers
                           if user.id != request.user.id           ]
            
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

            elif request.POST['teacher_selected'] in txtTeachers.split(','):
                error = 'Error - You already added this teacher as a coteacher!'

            if error:
                return render_to_response(self.baseDir()+'coteachers.html', request,{'class':cls,
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
                for teacher in cls.get_teachers():
                    cls.removeTeacher(teacher)

                # add bits for all new (and old) coteachers
                ccc = ClassCreationController(self.program)
                for teacher in coteachers:
                    ccc.associate_teacher_with_class(cls, teacher)
                ccc.send_class_mail_to_directors(cls)
                return self.goToCore(tl)


        
        return render_to_response(self.baseDir()+'coteachers.html', request, {'class':cls,
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
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        cls = classes[0]

        if cls.category == self.program.open_class_category:
            action = 'editopenclass'
        else:
            action = 'edit'
        
        module_list = prog.getModules()
        for mod in module_list:
            if isinstance(mod, TeacherClassRegModule):
                return mod.makeaclass_logic(request,  tl, one, two, module, extra, prog, cls, action=action)

    @aux_call
    @needs_admin
    def teacherlookup(self, request, tl, one, two, module, extra, prog, newclass = None):
        # Search for teachers with names that start with search string
        if not request.GET.has_key('name') or request.POST.has_key('name'):
            return self.goToCore(tl)
        
        return TeacherClassRegModule.teacherlookup_logic(request, tl, one, two, module, extra, prog, newclass)

    class Meta:
        proxy = True

