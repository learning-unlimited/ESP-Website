
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
  Email: web-team@lists.learningu.org
"""
from esp.program.modules.base    import ProgramModuleObj, needs_teacher, meets_deadline, main_call, aux_call
from esp.program.modules.module_ext     import ClassRegModuleInfo
from esp.program.modules         import module_ext
from esp.program.modules.forms.teacherreg   import TeacherClassRegForm, TeacherOpenClassRegForm
from esp.program.models          import ClassSubject, ClassSection, ClassCategories, ClassImplication, Program, StudentAppQuestion, ProgramModule, StudentRegistration, RegistrationType
from esp.program.controllers.classreg import ClassCreationController, ClassCreationValidationError, get_custom_fields
from esp.datatree.models import *
from esp.tagdict.models          import Tag
from esp.web.util                import render_to_response
from django.template.loader      import render_to_string
from esp.middleware              import ESPError
from django.utils.datastructures import MultiValueDict
from django.core.mail            import send_mail
from django.template.loader      import render_to_string
from django.http                 import HttpResponse
from esp.miniblog.models         import Entry
from django.core.cache           import cache
from django.db.models.query      import Q
from esp.users.models            import User, ESPUser
from esp.resources.models        import ResourceType, ResourceRequest
from esp.resources.forms         import ResourceRequestFormSet, ResourceTypeFormSet
from datetime                    import timedelta
from esp.mailman                 import add_list_member
from django.http                 import HttpResponseRedirect
import simplejson as json

class TeacherClassRegModule(ProgramModuleObj, module_ext.ClassRegModuleInfo):
    """ This program module allows teachers to register classes, and for them to modify classes/view class statuses
        as the program goes on. It is suggested, though not required, that this module is used in conjunction with
        StudentClassRegModule. Please be mindful of all the options of this module. """
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Teacher Class Registration",
            "link_title": "Register Your Classes",
            "module_type": "teach",
            "seq": 10,
            "main_call": "listclasses"
            }

    
    def extensions(self):
        """ This function gives all the extensions...that is, models that act on the join of a program and module."""
        return []#(., module_ext.ClassRegModuleInfo)] # ClassRegModuleInfo has important information for this module


    def prepare(self, context={}):
        """ prepare returns the context for the main teacherreg page. This will just set the teacherclsmodule as this module,
            since everything else can be gotten from hooks. """
        
        context['can_edit'] = self.deadline_met('/Classes/Edit')
        context['can_create'] = self.deadline_met('/Classes/Create')
        context['teacherclsmodule'] = self # ...
        return context


    def noclasses(self):
        """ Returns true of there are no classes in this program """
        return len(self.clslist()) < 1

    def isCompleted(self):
        return not self.noclasses()


    def teachers(self, QObject = False):
        #   New approach: Pile the class datatree anchor IDs into the appropriate lists.
        
        rejected_list = [x['anchor'] for x in self.program.classes().filter(status__lt=0).values('anchor')]
        approved_list = [x['anchor'] for x in self.program.classes().filter(status__gt=0).values('anchor')]
        proposed_list = [x['anchor'] for x in self.program.classes().filter(status=0).values('anchor')]
        Q_isteacher = Q(userbit__verb = GetNode('V/Flags/Registration/Teacher'))
        Q_rejected_teacher = Q(userbit__qsc__in=rejected_list) & Q_isteacher
        Q_approved_teacher = Q(userbit__qsc__in=approved_list) & Q_isteacher
        Q_proposed_teacher = Q(userbit__qsc__in=proposed_list) & Q_isteacher

        nearly_full_classes = [x.anchor for x in self.program.classes().filter(status__gt=0) if x.is_nearly_full()]
        Q_nearly_full_teacher = Q(userbit__qsc__in=nearly_full_classes) & Q_isteacher
        full_classes = [x.anchor for x in self.program.classes().filter(status__gt=0) if x.isFull()]
        Q_full_teacher = Q(userbit__qsc__in=full_classes) & Q_isteacher

        if QObject:
            return {'class_approved': self.getQForUser(Q_approved_teacher),
                    'class_proposed': self.getQForUser(Q_proposed_teacher),
                    'class_rejected': self.getQForUser(Q_rejected_teacher),
                    'class_nearly_full': self.getQForUser(Q_nearly_full_teacher),
                    'class_full': self.getQForUser(Q_full_teacher)}

        else:
            return {'class_approved': User.objects.filter(Q_approved_teacher).distinct(),
                    'class_proposed': User.objects.filter(Q_proposed_teacher).distinct(),
                    'class_rejected': User.objects.filter(Q_rejected_teacher).distinct(),
                    'class_nearly_full': User.objects.filter(Q_nearly_full_teacher).distinct(),
                    'class_full': User.objects.filter(Q_full_teacher).distinct()}


    def teacherDesc(self):
        capacity_factor = ClassSubject.get_capacity_factor()
        return {'class_approved': """Teachers teaching an approved class.""",
                'class_proposed': """Teachers teaching a class which has yet to be reviewed.""",
                'class_rejected': """Teachers teaching a rejected class.""",
                'class_full': """Teachers teaching a completely full class.""",
                'class_nearly_full': """Teachers teaching a nearly-full class (>%d%% of capacity).""" % (100 * capacity_factor)}

    
    def deadline_met(self, extension=''):
        if self.user.isAdmin(self.program):
            return True
        
        if len(extension) > 0:
            return super(TeacherClassRegModule, self).deadline_met(extension)

        tmpModule = ProgramModuleObj()
        tmpModule.__dict__ = self.__dict__
        return tmpModule.deadline_met('/Classes/Create') or tmpModule.deadline_met('/Classes/Edit')
    
    def clslist(self):
        return [cls for cls in self.user.getTaughtClasses()
                if cls.parent_program.id == self.program.id ]

    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/View")
    def section_students(self, request, tl, one, two, module, extra, prog):
    
        section = ClassSection.objects.filter(id=extra)
        if section.count() != 1:
            raise ESPError(False), 'Could not find that class section; please contact the webmasters.'

        return render_to_response(self.baseDir()+'class_students.html', request, (prog, tl), {'section': section[0], 'cls': section[0]})

    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/View")
    def class_students(self, request, tl, one, two, module, extra, prog):
    
        cls = ClassSubject.objects.filter(id=extra)
        if cls.count() != 1:
            raise ESPError(False), 'Could not find that class subject; please contact the webmasters.'

        return render_to_response(self.baseDir()+'class_students.html', request, (prog, tl), {'cls': cls[0]})
        
        
    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/SelectStudents")
    def select_students(self, request, tl, one, two, module, extra, prog):
        from esp.users.models import UserBit
        #   Get preregistered and enrolled students
        try:
            sec = ClassSection.objects.filter(id=extra)[0]
        except:
            raise ESPError(False), 'Class section not found.  If you came from a link on our site, please notify the webmasters.'
        
        students_list = sec.students_prereg()
        
        if request.method == 'POST':
            #   Handle form submission
            #   result_strs = []
            data = request.POST.copy()
            sections_dict = {}
            for key in data:
                key_dir = key.split('_')
                if key_dir[0] == 'regstatus' and len(key_dir) == 3:
                    student_id = int(key_dir[1])
                    sec_id = int(key_dir[2])
                    if sec_id not in sections_dict:
                        sections_dict[sec_id] = [{'id':student_id, 'status': data[key]}]
                    else:
                        sections_dict[sec_id].append({'id':student_id, 'status': data[key]})
            
            for sec_id in sections_dict:
                sec = ClassSection.objects.get(id=sec_id)
                sec.cache['students'] = None
                sec.cache['num_students'] = None
                for item in sections_dict[sec_id]:
                    student = ESPUser(User.objects.get(id=item['id']))
                    ignore = False
                    value = item['status']
                    if value == 'enroll':
                        verb_name = 'Enrolled'
                    elif value == 'reject':
                        verb_name = 'Rejected'
                    else:
                        ignore = True
                        
                    if not ignore:
                        rel = RegistrationType.get_map(include=['Enrolled', 'Rejected'], category='student')[verb_name]
                        other_regs = sec.getRegistrations(student).filter(relationship__name__in=['Enrolled', 'Rejected'])
                        found = False
                        for reg in other_regs:
                            if not found and reg.relationship == rel:
                                found = True
                            else:
                                reg.expire()
                            #   result_strs.append('Expired: %s' % bit)
                        if not found:
                            new_reg = StudentRegistration(user=student, relationship=rel, section=sec)
                            new_reg.save()
                        
        #   Jazz up this information a little
        for student in students_list:
            student.bits = sec.getRegVerbs(student)
            student.app = student.getApplication(self.program, False)
            student.other_classes = [(sec2, sec2.getRegVerbs(student)) for sec2 in student.getSections(self.program).exclude(id=sec.id)]
            preregs = sec.getRegistrations(student).exclude(relationship__name__in=['Enrolled', 'Rejected'])
            if preregs.count() != 0:
               student.added_class = preregs[0].start_date
            if 'Enrolled' in student.bits:
                student.enrolled = True
            elif 'Rejected' in student.bits:
                student.rejected = True

        #   Detect if there is an application module
        from esp.program.modules.handlers.studentjunctionappmodule import StudentJunctionAppModule
        has_app_module = False
        for module in prog.getModules():
            if isinstance(module, StudentJunctionAppModule):
                has_app_module = True

        return render_to_response(self.baseDir()+'select_students.html', request, (prog, tl), {'has_app_module': has_app_module, 'prog': prog, 'sec': sec, 'students_list': students_list})
        
    @aux_call
    @needs_teacher
    @meets_deadline('/Classes')
    def deleteclass(self, request, tl, one, two, module, extra, prog):
        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) != 1 or not self.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, (prog, tl),{})
        cls = classes[0]
        if cls.num_students() > 0:
            return render_to_response(self.baseDir()+'toomanystudents.html', request, (prog, tl), {})
        
        cls.delete()
        return self.goToCore(tl)

    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/View")
    def class_status(self, request, tl, one, two, module, extra, prog):
        clsid = 0
        if request.POST.has_key('clsid'):
            clsid = request.POST['clsid']
        else:
            clsid = extra
            
        classes = ClassSubject.objects.filter(id = clsid)
        if len(classes) != 1 or not self.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, (prog, tl),{})
        cls = classes[0]

        context = {'cls': cls, 'module': self,
                   'blogposts': Entry.find_posts_by_perms(self.user,GetNode('V/Subscribe'),cls.anchor)
                  }

        return render_to_response(self.baseDir()+'class_status.html', request, (prog, tl), context)

    @aux_call
    @needs_teacher
    @meets_deadline("/MainPage")
    def class_docs(self, request, tl, one, two, module, extra, prog):
        from esp.web.forms.fileupload_form import FileUploadForm    
        from esp.qsdmedia.models import Media

        clsid = 0
        if request.POST.has_key('clsid'):
            clsid = request.POST['clsid']
        else:
            clsid = extra
            
        classes = ClassSubject.objects.filter(id = clsid)
        if len(classes) != 1 or not self.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, (prog, tl),{})
        
        target_class = classes[0]
        context_form = FileUploadForm()
    
        if request.method == 'POST':
            if request.POST['command'] == 'delete':
                docid = request.POST['docid']
                media = Media.objects.get(id = docid)
                media.delete()
            	
            elif request.POST['command'] == 'add':
                form = FileUploadForm(request.POST, request.FILES)

                if form.is_valid():
                    media = Media(friendly_name = form.cleaned_data['title'], anchor = target_class.anchor)
                    ufile = form.cleaned_data['uploadedfile']
                    
                    #	Append the class code on the filename
                    desired_filename = '%s_%s' % (target_class.emailcode(), ufile.name)
                    media.handle_file(ufile, desired_filename)
                    
                    media.format = ''
                    media.save()
                else:
                    context_form = form
        
        context = {'cls': target_class, 'uploadform': context_form, 'module': self}
    
        return render_to_response(self.baseDir()+'class_docs.html', request, (prog, tl), context)

    @aux_call
    @needs_teacher
    @meets_deadline('/MainPage')
    def coteachers(self, request, tl, one, two, module, extra, prog): 
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
            add_list_member("%s_%s-teachers" % (prog.anchor.parent.name, prog.anchor.name), coteachers)

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
                                                                                                 'error': error,
                                                                                                 'conflicts': []})
            
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
            old_coteachers_set = set(cls.teachers())
            new_coteachers_set = set(coteachers)

            to_be_added = new_coteachers_set - old_coteachers_set
            to_be_deleted = old_coteachers_set - new_coteachers_set

            # don't delete the current user
            if self.user in to_be_deleted:
                to_be_deleted.remove(self.user)

            for teacher in to_be_added:
                if cls.conflicts(teacher):
                    conflictingusers.append(teacher.first_name+' '+teacher.last_name)

            if len(conflictingusers) == 0:
                # remove some old coteachers
                for teacher in to_be_deleted:
                    cls.removeTeacher(teacher)
                    cls.removeAdmin(teacher)

                # add bits for all new coteachers
                for teacher in to_be_added:
                    self.program.teacherSubscribe(teacher)
                    cls.makeTeacher(teacher)
                    cls.subscribe(teacher)
                    cls.makeAdmin(teacher, self.teacher_class_noedit)                    
                cls.update_cache()
                return self.goToCore(tl)


        
        return render_to_response(self.baseDir()+'coteachers.html', request, (prog, tl),{'class':cls,
                                                                                         'ajax':ajax,
                                                                                         'txtTeachers': txtTeachers,
                                                                                         'coteachers':  coteachers,
                                                                                         'conflicts':   conflictingusers})

    @needs_teacher
    def ajax_requests(self, request, tl, one, two, module, extra, prog):
        """ Handle a request for modifying a ResourceRequestFormSet. 
            This view is customized to handle the dynamic form
            (i.e. resource type is specified in advance and loaded
            into a hidden field). 
        """

        static_resource_requests = Tag.getProgramTag('static_resource_requests', prog, )

        #   Construct a formset from post data
        resource_formset = ResourceRequestFormSet(request.POST, prefix='request', static_resource_requests=static_resource_requests, )
        validity = resource_formset.is_valid()
        form_dicts = [x.__dict__ for x in resource_formset.forms]
        
        #   Retrieve data from forms
        form_datas = [x.cleaned_data for x in resource_formset.forms if hasattr(x, 'cleaned_data')]
        form_datas_filtered = [x for x in form_datas if x.has_key('resource_type')]
        
        if request.POST.has_key('action'):
            #   Modify form if an action is specified
            if request.POST['action'] == 'add':
                #   Construct initial data including new form
                new_restype = ResourceType.objects.get(id=request.POST['restype'])
                if len(new_restype.choices) > 0:
                    new_data = form_datas_filtered + [{'desired_value': new_restype.choices[0]}]
                else:
                    new_data = form_datas_filtered + [{}]
                new_types = [x['resource_type'] for x in form_datas_filtered] + [new_restype]
            elif request.POST['action'] == 'remove':
                #   Construct initial data removing undesired form
                form_to_remove = int(request.POST['form'])
                new_data = form_datas_filtered[:form_to_remove] + form_datas_filtered[(form_to_remove + 1):]
                new_types = [x['resource_type'] for x in new_data]
            
            #   Instantiate a new formset having the additional form
            new_formset = ResourceRequestFormSet(initial=new_data, resource_type=new_types, prefix='request', static_resource_requests=static_resource_requests, )
        else:
            #   Otherwise, just send back the original form
            new_formset = resource_formset
        
        #   Render an HTML fragment with the new formset
        context = {}
        context['program'] = prog
        context['formset'] = new_formset
        context['ajax_request'] = True
        formset_str = render_to_string(self.baseDir()+'requests_form_fragment.html', context)
        formset_script = render_to_string(self.baseDir()+'requests_form_fragment.js', context)
        return HttpResponse(json.dumps({'request_forms_html': formset_str, 'script': formset_script}))

    @needs_teacher
    def ajax_restypes(self, request, tl, one, two, module, extra, prog):
        """ Handle a request for modifying a ResourceTypeFormSet. 
            This is pretty straightforward and should be generalized for
            all further applications.
        """
        #   Construct a formset from post data
        resource_formset = ResourceTypeFormSet(request.POST, prefix='restype')
        validity = resource_formset.is_valid()
        form_dicts = [x.__dict__ for x in resource_formset.forms]
        
        #   Retrieve data from forms
        form_datas = [x.cleaned_data for x in resource_formset.forms if hasattr(x, 'cleaned_data')]
        form_datas_filtered = form_datas
        
        if request.POST.has_key('action'):
            #   Modify form if an action is specified
            if request.POST['action'] == 'add':
                #   Construct initial data including new form
                new_data = form_datas_filtered + [{}]
            elif request.POST['action'] == 'remove':
                #   Construct initial data removing undesired form
                form_to_remove = int(request.POST['form'])
                new_data = form_datas_filtered[:form_to_remove] + form_datas_filtered[(form_to_remove + 1):]

            #   Instantiate a new formset having the additional form
            new_formset = ResourceTypeFormSet(initial=new_data, prefix='restype')
        else:
            #   Otherwise, just send back the original form
            new_formset = resource_formset
        
        #   Render an HTML fragment with the new formset
        context = {}
        context['program'] = prog
        context['formset'] = new_formset
        context['ajax_request'] = True
        formset_str = render_to_string(self.baseDir()+'restype_form_fragment.html', context)
        formset_script = render_to_string(self.baseDir()+'restype_form_fragment.js', context)
        return HttpResponse(json.dumps({'restype_forms_html': formset_str, 'script': formset_script}))
        
    @aux_call
    @meets_deadline("/Classes/Edit")
    @needs_teacher
    def editclass(self, request, tl, one, two, module, extra, prog):
        try:
            int(extra)
        except: 
            raise ESPError("False"), "Invalid integer for class ID!"

        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) == 0:
            raise ESPError("False"), "No class found matching this ID!"

        if len(classes) != 1 or not self.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, (prog, tl),{})
        cls = classes[0]

        # Dirty hack to special-case the new "open classes".  Feel free to make more general/elegant. --rye
        if cls.category.category == "Walk-in Seminar":
            action = 'editopenclass'
        else:
            action = 'edit'

        return self.makeaclass_logic(request, tl, one, two, module, extra, prog, cls, action)

    @aux_call
    @meets_deadline('/Classes/Create')
    @needs_teacher
    def makeaclass(self, request, tl, one, two, module, extra, prog, newclass = None):
        return self.makeaclass_logic(request, tl, one, two, module, extra, prog, newclass = None)

    @aux_call
    @meets_deadline('/Classes/Create')
    @needs_teacher
    def makeopenclass(self, request, tl, one, two, module, extra, prog, newclass = None):
        return self.makeaclass_logic(request, tl, one, two, module, extra, prog, newclass = None, action = 'createopenclass')


    def makeaclass_logic(self, request, tl, one, two, module, extra, prog, newclass = None, action = 'create'):
        context = {'module': self}
        
        static_resource_requests = Tag.getProgramTag('static_resource_requests', self.program, )

        if request.method == 'POST' and request.POST.has_key('class_reg_page'):
            if not self.deadline_met():
                return self.goToCore(tl)

            ccc = ClassCreationController(self.program)

            try:
                if action == 'create':
                    newclass = ccc.makeaclass(request.user, request.POST)
                elif action == 'createopenclass':
                    newclass = ccc.makeaclass(request.user, request.POST, form_class=TeacherOpenClassRegForm)
                elif action == 'edit':
                    newclass = ccc.editclass(request.user, request.POST, extra)
                elif action == 'editopenclass':
                    newclass = ccc.editclass(request.user, request.POST, extra, form_class=TeacherOpenClassRegForm)

                do_question = bool(ProgramModule.objects.filter(handler="TeacherReviewApps", program=self.program))

                if do_question:
                    return HttpResponseRedirect(newclass.parent_program.get_teach_url() + "app_questions")
                return self.goToCore(tl)

            except ClassCreationValidationError, e:
                reg_form = e.reg_form
                resource_formset = e.resource_formset
                restype_formset = e.restype_formset

        else:
            errors = {}
            
            default_restypes = Tag.getProgramTag('default_restypes', program=self.program, )
            if default_restypes:
                resource_type_labels = json.loads(default_restypes)
                resource_types = [ResourceType.get_or_create(x, self.program) for x in resource_type_labels]
            else:
                if static_resource_requests:
                    # With static resource requests, we need to display a form
                    # each available type --- there's no way to add the types
                    # that we didn't start out with
                    # Thus, if default_restype isn't set, we display everything
                    # potentially relevant
                    q_program = Q(program=self.program)
                    if Tag.getTag('allow_global_restypes'):
                        q_program = q_program | Q(program__isnull=True)
                    resource_types=list(ResourceType.objects.filter(q_program).order_by('-priority_default'))
                else:
                    # If we're not using static resource requests, then just
                    # hardcode some sane defaults
                    resource_type_labels = ['Classroom', 'A/V']
                    resource_types = [ResourceType.get_or_create(x, self.program) for x in resource_type_labels]

            if newclass is not None:
                current_data = newclass.__dict__
                # Duration can end up with rounding errors. Pick the closest.
                old_delta = None
                # Technically, this is a "backwards compatibility" field, so we put in a hack
                # for the "correct" usage. This feels silly. Why are ClassSections allowed different
                # durations when every interface assumes they're identical?
                current_duration = current_data['duration'] or newclass.sections.all()[0].duration
                rounded_duration = 0
                for k, v in self.getDurations() + [(0,'')]:
                    new_delta = abs( k - current_duration )
                    if old_delta is None or new_delta < old_delta:
                        old_delta = new_delta
                        rounded_duration = k
                current_data['duration'] = rounded_duration
                current_data['category'] = newclass.category.id
                current_data['num_sections'] = newclass.sections.count()
                current_data['allow_lateness'] = newclass.allow_lateness
                current_data['title'] = newclass.anchor.friendly_name
                current_data['url']   = newclass.anchor.name
                for field_name in get_custom_fields():
                    if field_name in newclass.custom_form_data:
                        current_data[field_name] = newclass.custom_form_data[field_name]
                if newclass.optimal_class_size_range:
                    current_data['optimal_class_size_range'] = newclass.optimal_class_size_range.id
                if newclass.allowable_class_size_ranges.all():
                    current_data['allowable_class_size_ranges'] = list(newclass.allowable_class_size_ranges.all().values_list('id', flat=True))
                context['class'] = newclass
                if action=='edit':
                    reg_form = TeacherClassRegForm(self, current_data)
                elif action=='editopenclass':
                    reg_form = TeacherOpenClassRegForm(self, current_data)
                
                #   Todo...
                ds = newclass.default_section()
                class_requests = ResourceRequest.objects.filter(target=ds)
                if static_resource_requests:
                    #   Program the multiple-checkbox forms if static requests are used.
                    resource_formset = ResourceRequestFormSet(resource_type=resource_types, prefix='request', static_resource_requests=static_resource_requests)
                    initial_requests = {}
                    for x in class_requests:
                        if x.res_type.name not in initial_requests:
                            initial_requests[x.res_type.name]  = []
                        initial_requests[x.res_type.name].append(x.desired_value)
                    for form in resource_formset.forms:
                        field = form.fields['desired_value']
                        if field.label in initial_requests:
                            field.initial = initial_requests[field.label]
                            if form.resource_type.only_one and len(field.initial):
                                field.initial = field.initial[0]
                else:
                    #   With dynamic requests each form uses radio buttons, so there's a one-to-one correspondence
                    #   between forms and requests.
                    resource_formset = ResourceRequestFormSet(
                        initial=[{'resource_type': x.res_type, 'desired_value': x.desired_value} for x in class_requests],
                        resource_type=[x.res_type for x in class_requests],
                        prefix='request',
                        static_resource_requests=static_resource_requests,
                    )
                restype_formset = ResourceTypeFormSet(initial=[], prefix='restype')

            else:
                if action=='create':
                    reg_form = TeacherClassRegForm(self)
                elif action=='createopenclass':
                    reg_form = TeacherOpenClassRegForm(self)

                #   Provide initial forms: a request for each provided type, but no requests for new types.
                resource_formset = ResourceRequestFormSet(resource_type=resource_types, prefix='request', static_resource_requests=static_resource_requests, )
                restype_formset = ResourceTypeFormSet(initial=[], prefix='restype')

        context['one'] = one
        context['two'] = two
        context['form'] = reg_form
        context['formset'] = resource_formset
        context['restype_formset'] = restype_formset
        context['allow_restype_creation'] = Tag.getProgramTag('allow_restype_creation', program=self.program, )
        context['static_resource_requests'] = static_resource_requests
        context['resource_types'] = self.program.getResourceTypes(include_classroom=True)
        
        if newclass is None:
            context['addoredit'] = 'Add'
        else:
            context['addoredit'] = 'Edit'

        if action == 'create' or action == 'edit':
            template_name = 'classedit.html'
        elif action == 'createopenclass' or action == 'editopenclass':
            template_name = 'openclassedit.html'

        return render_to_response(self.baseDir() + template_name, request, (prog, tl), context)


    @aux_call
    @needs_teacher    
    def teacherlookup(self, request, tl, one, two, module, extra, prog, newclass = None):
        limit = 10
        from esp.web.views.json import JsonResponse
        from esp.users.models import UserBit

        Q_teacher = Q(userbit__verb = GetNode('V/Flags/UserRole/Teacher'))

        # Search for teachers with names that start with search string
        if not request.GET.has_key('name') or request.POST.has_key('name'):
            return self.goToCore(tl)

        queryset = User.objects.filter(Q_teacher)
        
        if not request.GET.has_key('name'):
            startswith = request.POST['name']
        else:
            startswith = request.GET['name']
        parts = [x.strip('*') for x in startswith.split(',')]
        
        #   Don't return anything if there's no input.
        if len(parts[0]) > 0:
            Q_name = Q(last_name__istartswith=parts[0])

            if len(parts) > 1:
                Q_name = Q_name & Q(first_name__istartswith=parts[1])

            # Isolate user objects
            queryset = queryset.filter(Q_name)[:(limit*10)]
            user_dict = {}
            for user in queryset:
                user_dict[user.id] = user
            users = user_dict.values()

            # Construct combo-box items
            obj_list = [{'name': "%s, %s" % (user.last_name, user.first_name), 'username': user.username, 'id': user.id} for user in users]
        else:
            obj_list = []

        return JsonResponse(obj_list)

    def getNavBars(self):
        """ Returns a list of the dictionary to render the class catalog, if it's open """
        if super(TeacherClassRegModule, self).deadline_met('/Catalog'):
            return [{ 'link': '/learn/%s/catalog' % ( self.program.getUrlBase() ),
                      'text': '%s Catalog' % ( self.program.niceName() ) }]
        
        else:
            return []

    def get_msg_vars(self, user, key):
        user = ESPUser(user)
        if key == 'full_classes':
            return user.getFullClasses_pretty(self.program)

        return 'No classes.'
