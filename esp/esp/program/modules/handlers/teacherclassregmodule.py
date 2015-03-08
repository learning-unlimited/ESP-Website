
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
from collections import defaultdict

from esp.program.modules.base    import ProgramModuleObj, needs_teacher, meets_deadline, main_call, aux_call, user_passes_test
from esp.program.modules.module_ext     import ClassRegModuleInfo
from esp.program.modules         import module_ext
from esp.program.modules.forms.teacherreg   import TeacherClassRegForm, TeacherOpenClassRegForm
from esp.program.models          import ClassSubject, ClassSection, ClassCategories, ClassImplication, Program, StudentAppQuestion, ProgramModule, StudentRegistration, RegistrationType, ClassFlagType
from esp.program.controllers.classreg import ClassCreationController, ClassCreationValidationError, get_custom_fields
from esp.tagdict.models          import Tag
from esp.tagdict.decorators      import require_tag
from esp.web.util                import render_to_response
from django.template.loader      import render_to_string
from esp.middleware              import ESPError
from django.utils.datastructures import MultiValueDict
from esp.dbmail.models           import send_mail
from django.template.loader      import render_to_string
from django.http                 import HttpResponse
from esp.miniblog.models         import Entry
from django.core.cache           import cache
from django.db.models.query      import Q
from esp.users.models            import User, ESPUser
from esp.resources.models        import ResourceType, ResourceRequest
from esp.resources.forms         import ResourceRequestFormSet, ResourceTypeFormSet
from datetime                    import timedelta
from esp.mailman                 import add_list_members
from django.http                 import HttpResponseRedirect
from django.db                   import models
from django.forms.util           import ErrorDict
from esp.middleware.threadlocalrequest import get_current_request
import simplejson as json
from copy import deepcopy

class TeacherClassRegModule(ProgramModuleObj):
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
            "inline_template": "listclasses.html",
            }

    @classmethod
    def extensions(cls):
        return {'crmi': module_ext.ClassRegModuleInfo}


    def prepare(self, context={}):
        """ prepare returns the context for the main teacherreg page. """
        
        context['can_edit'] = self.deadline_met('/Classes/Edit')
        context['can_create'] = self.any_reg_is_open()
        context['can_create_class'] = self.class_reg_is_open()
        context['can_create_open_class'] = self.open_class_reg_is_open()
        context['crmi'] = self.crmi
        context['clslist'] = self.clslist(get_current_request().user)
        context['friendly_times_with_date'] = (Tag.getProgramTag(key='friendly_times_with_date',program=self.program,default=False) == "True")
        context['allow_class_import'] = 'false' not in Tag.getTag('allow_class_import', default='true').lower()
        context['open_class_category'] = self.program.open_class_category.category
        return context


    def noclasses(self):
        """ Returns true of there are no classes in this program """
        return len(self.clslist(get_current_request().user)) < 1

    def isCompleted(self):
        return not self.noclasses()

    def get_resource_pairs(self):
        items = []
        for res_type in self.program.getResourceTypes():
            possible_values = res_type.resourcerequest_set.values_list('desired_value', flat=True).distinct()
            for i in range(len(possible_values)):
                val = possible_values[i]
                label = 'teacher_res_%d_%d' % (res_type.id, i)
                full_description = 'Teachers who requested "%s" for their %s' % (val, res_type.name)
                query = Q(classsubject__sections__resourcerequest__res_type=res_type, classsubject__sections__resourcerequest__desired_value=val, classsubject__sections__parent_class__parent_program=self.program)
                items.append((label, full_description, query))
        return items

    def teachers(self, QObject = False):
        fields_to_defer = [x.name for x in ClassSubject._meta.fields if isinstance(x, models.TextField)]
        classes_qs = self.program.classes().defer(*fields_to_defer)

        Q_isteacher = Q(classsubject__in=classes_qs)
        Q_rejected_teacher = Q(classsubject__in=classes_qs.filter(status__lt=0)) & Q_isteacher
        Q_approved_teacher = Q(classsubject__in=classes_qs.filter(status__gt=0)) & Q_isteacher
        Q_proposed_teacher = Q(classsubject__in=classes_qs.filter(status=0)) & Q_isteacher

        ## is_nearly_full() means at least one section is more than float(ClassSubject.get_capacity_factor()) full
        ## isFull() means that all *scheduled* sections are full
        ## Querying the full catalog is overkill here, but we do use a fair bit of it..., and hopefully it's
        ## better cached than other simpler queries that we might use.
        classes = ClassSubject.objects.catalog(self.program)
        capacity_factor = ClassSubject.get_capacity_factor()
        nearly_full_classes = [x for x in classes if x.is_nearly_full(capacity_factor)]
        Q_nearly_full_teacher = Q(classsubject__in=nearly_full_classes) & Q_isteacher
        full_classes = [x for x in classes if x.isFull()]
        Q_full_teacher = Q(classsubject__in=full_classes) & Q_isteacher

        #   With the new schema it is impossible to make a single Q object for
        #   teachers who have taught for a previous program and teachers
        #   who are teaching for the current program.  You have to chain calls
        #   to .filter().
        Q_taught_before = Q(classsubject__status=10, classsubject__parent_program__in=Program.objects.exclude(pk=self.program.pk))

        #   Add dynamic queries for checking for teachers with particular resource requests
        additional_qs = {}
        for item in self.get_resource_pairs():
            additional_qs[item[0]] = Q_isteacher & (Q_rejected_teacher | Q_approved_teacher | Q_proposed_teacher) & item[2]

        if QObject:
            result = {
                'class_submitted': self.getQForUser(Q_isteacher),
                'class_approved': self.getQForUser(Q_approved_teacher),
                'class_proposed': self.getQForUser(Q_proposed_teacher),
                'class_rejected': self.getQForUser(Q_rejected_teacher),
                'class_nearly_full': self.getQForUser(Q_nearly_full_teacher),
                'class_full': self.getQForUser(Q_full_teacher),
                'taught_before': self.getQForUser(Q_taught_before),     #   not exactly correct, see above
            }
            for key in additional_qs:
                result[key] = self.getQForUser(additional_qs[key])
        else:
            result = {
                'class_submitted': ESPUser.objects.filter(Q_isteacher).distinct(),
                'class_approved': ESPUser.objects.filter(Q_approved_teacher).distinct(),
                'class_proposed': ESPUser.objects.filter(Q_proposed_teacher).distinct(),
                'class_rejected': ESPUser.objects.filter(Q_rejected_teacher).distinct(),
                'class_nearly_full': ESPUser.objects.filter(Q_nearly_full_teacher).distinct(),
                'class_full': ESPUser.objects.filter(Q_full_teacher).distinct(),
                'taught_before': ESPUser.objects.filter(Q_isteacher).filter(Q_taught_before).distinct(),
            }
            for key in additional_qs:
                result[key] = ESPUser.objects.filter(additional_qs[key]).distinct()
                
        return result

    def teacherDesc(self):
        capacity_factor = ClassSubject.get_capacity_factor()
        result = {
            'class_submitted': """Teachers who have submitted at least one class""",
            'class_approved': """Teachers teaching an approved class""",
            'class_proposed': """Teachers teaching an unreviewed class""",
            'class_rejected': """Teachers teaching a rejected class""",
            'class_full': """Teachers teaching a completely full class""",
            'class_nearly_full': """Teachers teaching a nearly-full class (>%d%% of capacity)""" % (100 * capacity_factor),
            'taught_before': """Teachers who have taught for a previous program""",
        }
        for item in self.get_resource_pairs():
            result[item[0]] = item[1]
        return result
    
    def deadline_met(self, extension=''):
        tmpModule = super(TeacherClassRegModule, self)
        if len(extension) > 0:
            return tmpModule.deadline_met(extension)
        else:
            return (self.any_reg_is_open()
                    or tmpModule.deadline_met('/Classes/Edit'))

    def class_reg_is_open(self):
        return self.deadline_met('/Classes/Create/Class')

    def open_class_reg_is_open(self):
        return (self.crmi.open_class_registration
                and self.deadline_met('/Classes/Create/OpenClass'))

    reg_is_open_methods = defaultdict(
        (lambda: (lambda self: False)),
        {
            'Class': class_reg_is_open,
            'OpenClass': open_class_reg_is_open,
        },
    )

    def reg_is_open(self, reg_type='Class'):
        return self.reg_is_open_methods[reg_type](self)

    def any_reg_is_open(self):
        return any(map(self.reg_is_open, self.reg_is_open_methods.keys()))

    def clslist(self, user):
        return [cls for cls in user.getTaughtClasses()
                if cls.parent_program_id == self.program.id ]

    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/View")
    def section_students(self, request, tl, one, two, module, extra, prog):
    
        section = ClassSection.objects.filter(id=extra)
        if section.count() != 1:
            raise ESPError('Could not find that class section; please contact the webmasters.', log=False)

        return render_to_response(self.baseDir()+'class_students.html', request, {'section': section[0], 'cls': section[0]})

    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/View")
    def class_students(self, request, tl, one, two, module, extra, prog):
    
        cls = ClassSubject.objects.filter(id=extra)
        if cls.count() != 1:
            raise ESPError('Could not find that class subject; please contact the webmasters.', log=False)

        return render_to_response(self.baseDir()+'class_students.html', request, {'cls': cls[0]})
        
        
    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/SelectStudents")
    def select_students(self, request, tl, one, two, module, extra, prog):
        #   Get preregistered and enrolled students
        try:
            sec = ClassSection.objects.filter(id=extra)[0]
        except:
            raise ESPError('Class section not found.  If you came from a link on our site, please notify the webmasters.', log=False)
        
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

                        if not found:
                            new_reg = StudentRegistration(user=student, relationship=rel, section=sec)
                            new_reg.save()
                        
        #   Jazz up this information a little
        #Not having much luck with query count/performance when selecting related parent_class and parent_class__category
        #Creating a lookup dict instead to strip out duplicate ClassSubject instances

        student_regs = StudentRegistration.valid_objects().filter(user__in=students_list) \
                       .order_by('start_date').select_related('section','user','relationship')
        student_regs = student_regs.filter(section__parent_class__parent_program=self.program)

        student_sections_dict = defaultdict(set)
        student_reg_dict = defaultdict(set)

        #need a unique set of parent_class ids
        #creating lookup dicts to avoid hitting database(was not solved with 
        #select_related or prefecth_related
        parent_class_id_set= set()
        sections = set()
        for reg in student_regs:
            student_sections_dict[reg.user].add(reg.section)
            display_name = reg.relationship.displayName or reg.relationship.name
            sections.add(reg.section)
            parent_class_id_set.add(reg.section.parent_class_id)
            student_reg_dict['%i_%i'%(reg.user.id,reg.section.id,)].add(display_name)

        subjects = ClassSubject.objects.filter(id__in=parent_class_id_set).select_related('category')
        subject_categories_dict = dict([(s.id, (s,s.category)) for s in subjects])

        for student in students_list:
            student.bits = student_reg_dict['%i_%i'%(student.id,sec.id,)]
            #this is a bit of a problem because it produces the side affect of application
            #creation if not found
            student.app = student.getApplication(self.program, False)
            student.other_classes = []
            for section in student_sections_dict[student]:
                parent_class,category = subject_categories_dict.get(section.parent_class_id)
                regtypes = student_reg_dict['%i_%i'%(student.id,section.id,)]

                section_row = (section,
                               regtypes,
                               parent_class,
                               category
                               )
                student.other_classes.append(section_row)
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

        return render_to_response(self.baseDir()+'select_students.html', request, {'has_app_module': has_app_module, 'prog': prog, 'sec': sec, 'students_list': students_list})
        
    @aux_call
    @needs_teacher
    @meets_deadline('/Classes')
    def deleteclass(self, request, tl, one, two, module, extra, prog):
        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        cls = classes[0]
        if cls.num_students() > 0:
            return render_to_response(self.baseDir()+'toomanystudents.html', request, {})
        
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
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        cls = classes[0]

        context = {'cls': cls, 'module': self,}

        return render_to_response(self.baseDir()+'class_status.html', request, context)

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
        if len(classes) != 1 or not request.user.canEdit(classes[0]):
                return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        
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
                    media = Media(friendly_name = form.cleaned_data['title'], owner = target_class)
                    ufile = form.cleaned_data['uploadedfile']
                    
                    #	Append the class code on the filename
                    desired_filename = '%s_%s' % (target_class.emailcode(), ufile.name)
                    media.handle_file(ufile, desired_filename)
                    
                    media.format = ''
                    media.save()
                else:
                    context_form = form
        
        context = {'cls': target_class, 'uploadform': context_form, 'module': self}
    
        return render_to_response(self.baseDir()+'class_docs.html', request, context)

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
            add_list_members("%s_%s-teachers" % (prog.program_type, prog.program_instance), coteachers)

        op = ''
        if request.POST.has_key('op'):
            op = request.POST['op']

        conflictingusers = []
        error = False
        
        if op == 'add':


            if len(request.POST['teacher_selected'].strip()) == 0:
                error = 'Error - Please click on the name when it drops down.'

            elif (request.POST['teacher_selected'] == str(request.user.id)):
                error = 'Error - You cannot select yourself as a coteacher!'
            elif request.POST['teacher_selected'] in txtTeachers.split(','):
                error = 'Error - You already added this teacher as a coteacher!'

            if error:
                return render_to_response(self.baseDir()+'coteachers.html', request, {'class':cls,
                                                                                     'ajax':ajax,
                                                                                     'txtTeachers': txtTeachers,
                                                                                     'coteachers':  coteachers,
                                                                                     'error': error,
                                                                                     'conflicts': []})

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
            old_coteachers_set = set(cls.get_teachers())
            new_coteachers_set = set(coteachers)

            to_be_added = new_coteachers_set - old_coteachers_set
            to_be_deleted = old_coteachers_set - new_coteachers_set

            # don't delete the current user
            if request.user in to_be_deleted:
                to_be_deleted.remove(request.user)

            for teacher in to_be_added:
                if cls.conflicts(teacher):
                    conflictingusers.append(teacher.first_name+' '+teacher.last_name)

            if len(conflictingusers) == 0:
                # remove some old coteachers
                for teacher in to_be_deleted:
                    cls.removeTeacher(teacher)

                # add bits for all new coteachers
                ccc = ClassCreationController(self.program)
                for teacher in to_be_added:
                    ccc.associate_teacher_with_class(cls, teacher)
                ccc.send_class_mail_to_directors(cls)
                return self.goToCore(tl)

        return render_to_response(self.baseDir()+'coteachers.html', request, {'class':cls,
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

        #   Construct a formset from post data
        resource_formset = ResourceRequestFormSet(request.POST, prefix='request')
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
            new_formset = ResourceRequestFormSet(initial=new_data, resource_type=new_types, prefix='request')
        else:
            #   Otherwise, just send back the original form
            new_formset = resource_formset
        
        #   Render an HTML fragment with the new formset
        context = {}
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
        context['formset'] = new_formset
        context['ajax_request'] = True
        formset_str = render_to_string(self.baseDir()+'restype_form_fragment.html', context)
        formset_script = render_to_string(self.baseDir()+'restype_form_fragment.js', context)
        return HttpResponse(json.dumps({'restype_forms_html': formset_str, 'script': formset_script}))
        
    @aux_call
    @needs_teacher
    @meets_deadline("/Classes/Edit")
    def editclass(self, request, tl, one, two, module, extra, prog):
        try:
            int(extra)
        except: 
            raise ESPError("Invalid integer for class ID!", log=False)

        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) == 0:
            raise ESPError("No class found matching this ID!", log=False)

        if len(classes) != 1 or not request.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, {})
        cls = classes[0]

        if cls.category == self.program.open_class_category:
            action = 'editopenclass'
        else:
            action = 'edit'

        return self.makeaclass_logic(request, tl, one, two, module, extra, prog, cls, action)

    @main_call
    @needs_teacher
    @meets_deadline('/Classes/Create/Class')
    def makeaclass(self, request, tl, one, two, module, extra, prog, newclass = None):
        return self.makeaclass_logic(request, tl, one, two, module, extra, prog, newclass = None)

    @aux_call
    @needs_teacher
    @meets_deadline('/Classes/Create/Class')
    def copyaclass(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            action = 'create'
            if request.POST.has_key('category'):
                category = request.POST['category']
                if category.isdigit() and int(category) == int(self.program.open_class_category.id):
                    action = 'createopenclass'
            return self.makeaclass_logic(request, tl, one, two, module, extra, prog, action=action)
        if not request.GET.has_key('cls'):
            raise ESPError("No class specified!", log=False)
        
        # Select the class
        cls_id = request.GET['cls']
        classes = ClassSubject.objects.filter(id=cls_id)
        if len(classes) == 0:
            raise ESPError("No class found matching this ID!", log=False)
        if len(classes) != 1:
            raise ESPError("Something weird happened, more than one class found matching this ID.", log=False)
        cls = classes[0]

        # Select the correct action
        if cls.category == self.program.open_class_category:
            action = 'editopenclass'
        else:
            action = 'edit'

        return self.makeaclass_logic(request, tl, one, two, module, extra, prog, cls, action, populateonly = True)

    @aux_call
    @needs_teacher
    @meets_deadline('/Classes/Create/Class')
    def copyclasses(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['all_class_list'] = request.user.getTaughtClasses()
        context['noclasses'] = (len(context['all_class_list']) == 0)
        context['allow_class_import'] = 'false' not in Tag.getTag('allow_class_import', default='true').lower()
        return render_to_response(self.baseDir()+'listcopyclasses.html', request, context)

    @aux_call
    @needs_teacher
    @user_passes_test(
        open_class_reg_is_open,
        (
            'the deadline Teacher/Classes/Create/OpenClass '
            'or the setting ClassRegModuleInfo.open_class_registration were'
        ),
    )
    def makeopenclass(self, request, tl, one, two, module, extra, prog, newclass = None):
        return self.makeaclass_logic(request, tl, one, two, module, extra, prog, newclass = None, action = 'createopenclass')


    def makeaclass_logic(self, request, tl, one, two, module, extra, prog, newclass = None, action = 'create', populateonly = False):
        """
        The logic for the teacher class registration form.

        A brief description of some of the key arguments:
        - newclass -- The class object from which to fill in the data
        - action -- What action is the form performing? Options are 'create',
              'createopenclass', 'edit', 'editopenclass'
        - populateonly -- If True and newclass is specified, the form will only
              populate the fields, rather than keeping track of which class they
              came from and saving edits back to that. This is used for the class
              copying logic.
        """

        context = {'module': self}
        
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
                if request.POST.has_key('manage') and request.POST['manage'] == 'manage':
                    if request.POST['manage_submit'] == 'reload':
                        return HttpResponseRedirect(request.get_full_path()+'?manage=manage')
                    elif request.POST['manage_submit'] == 'manageclass':
                        return HttpResponseRedirect('/manage/%s/manageclass/%s' % (self.program.getUrlBase(), extra))
                    elif request.POST['manage_submit'] == 'dashboard':
                        return HttpResponseRedirect('/manage/%s/dashboard' % self.program.getUrlBase())
                    elif request.POST['manage_submit'] == 'main':
                        return HttpResponseRedirect('/manage/%s/main' % self.program.getUrlBase())
                return self.goToCore(tl)

            except ClassCreationValidationError, e:
                reg_form = e.reg_form
                resource_formset = e.resource_formset
                restype_formset = e.restype_formset

        else:
            # With static resource requests, we need to display a form
            # each available type --- there's no way to add the types
            # that we didn't start out with
            # Thus, if default_restype isn't set, we display everything
            # potentially relevant
            if Tag.getTag('allow_global_restypes'):
                resource_types = prog.getResourceTypes(include_classroom=True,
                                                       include_global=True)
            else:
                resource_types = prog.getResourceTypes(include_classroom=True)
            resource_types = list(resource_types)
            resource_types.reverse()

            if newclass is not None:
                current_data = newclass.__dict__
                # Duration can end up with rounding errors. Pick the closest.
                old_delta = None
                # Technically, this is a "backwards compatibility" field, so we put in a hack
                # for the "correct" usage. This feels silly. Why are ClassSections allowed different
                # durations when every interface assumes they're identical?
                current_duration = current_data['duration'] or newclass.sections.all()[0].duration
                rounded_duration = 0
                for k, v in self.crmi.getDurations() + [(0,'')]:
                    new_delta = abs( k - current_duration )
                    if old_delta is None or new_delta < old_delta:
                        old_delta = new_delta
                        rounded_duration = k
                current_data['duration'] = rounded_duration
                current_data['category'] = newclass.category.id
                current_data['num_sections'] = newclass.sections.count()
                current_data['allow_lateness'] = newclass.allow_lateness
                current_data['title'] = newclass.title
                current_data['url']   = newclass.emailcode()
                for field_name in get_custom_fields():
                    if field_name in newclass.custom_form_data:
                        current_data[field_name] = newclass.custom_form_data[field_name]
                if newclass.optimal_class_size_range:
                    current_data['optimal_class_size_range'] = newclass.optimal_class_size_range.id
                if newclass.allowable_class_size_ranges.all():
                    current_data['allowable_class_size_ranges'] = list(newclass.allowable_class_size_ranges.all().values_list('id', flat=True))

                # Makes importing a class from a previous program work
                # These are the only three fields that can currently be hidden
                # If another one is added later, this will need to be changed
                hidden_fields = Tag.getProgramTag('teacherreg_hide_fields', prog)
                if hidden_fields:
                    if 'grade_min' in hidden_fields:
                        current_data['grade_min'] = Tag.getProgramTag('teacherreg_default_min_grade', prog)
                    if 'grade_max' in hidden_fields:
                        current_data['grade_max'] = Tag.getProgramTag('teacherreg_default_max_grade', prog)
                    if 'class_size_max' in hidden_fields:
                        current_data['class_size_max'] = Tag.getProgramTag('teacherreg_default_class_size_max', prog)

                if not populateonly:
                    context['class'] = newclass

                if action=='edit':
                    reg_form = TeacherClassRegForm(self, current_data)
                    if populateonly: reg_form._errors = ErrorDict()
                elif action=='editopenclass':
                    reg_form = TeacherOpenClassRegForm(self, current_data)
                    if populateonly: reg_form._errors = ErrorDict()
                
                #   Todo...
                ds = newclass.default_section()
                class_requests = ResourceRequest.objects.filter(target=ds)
                #   Program the multiple-checkbox forms if static requests are used.
                resource_formset = ResourceRequestFormSet(resource_type=resource_types, prefix='request')
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
                restype_formset = ResourceTypeFormSet(initial=[], prefix='restype')

            else:
                if action=='create':
                    reg_form = TeacherClassRegForm(self)
                elif action=='createopenclass':
                    reg_form = TeacherOpenClassRegForm(self)

                #   Provide initial forms: a request for each provided type, but no requests for new types.
                resource_formset = ResourceRequestFormSet(resource_type=resource_types, prefix='request')
                restype_formset = ResourceTypeFormSet(initial=[], prefix='restype')

        context['tl'] = 'teach'
        context['one'] = one
        context['two'] = two
        context['form'] = reg_form
        context['formset'] = resource_formset
        context['restype_formset'] = restype_formset
        context['allow_restype_creation'] = Tag.getProgramTag('allow_restype_creation', program=self.program, )
        context['resource_types'] = self.program.getResourceTypes(include_classroom=True)
        context['classroom_form_advisories'] = 'classroom_form_advisories'
        if self.program.grade_max - self.program.grade_min >= 4:
            context['grade_range_popup'] = (Tag.getProgramTag('grade_range_popup', self.program) != "False")
        else:
            context['grade_range_popup'] = False

        if newclass is None:
            context['addoredit'] = 'Add'
        else:
            context['addoredit'] = 'Edit'

        context['classes'] = {
            0: {
                'type': 'class',
                'link': 'makeaclass',
                'reg_open': self.class_reg_is_open(),
            },
            1: {
                'type': self.program.open_class_category.category,
                'link': 'makeopenclass',
                'reg_open': self.open_class_reg_is_open(),
            }
        }
        if action == 'create' or action == 'edit':
            context['isopenclass'] = 0
        elif action == 'createopenclass' or action == 'editopenclass':
            context['isopenclass'] = 1
            context['grade_range_popup'] = False
            context['classroom_form_advisories'] += '__open_class'
        context['classtype'] = context['classes'][context['isopenclass']]['type']
        context['otherclass'] = context['classes'][1 - context['isopenclass']]
        context['qsd_name'] = 'classedit_' + context['classtype']

        context['manage'] = False
        if ((request.method == "POST" and request.POST.has_key('manage') and request.POST['manage'] == 'manage') or 
            (request.method == "GET" and request.GET.has_key('manage') and request.GET['manage'] == 'manage') or
            (tl == 'manage' and 'class' in context)) and request.user.isAdministrator():
            context['manage'] = True
            if self.program.program_modules.filter(handler='ClassFlagModule').exists():
                context['show_flags'] = True
                context['flag_types'] = ClassFlagType.get_flag_types(self.program)
        
        return render_to_response(self.baseDir() + 'classedit.html', request, context)


    @aux_call
    @needs_teacher    
    def teacherlookup(self, request, tl, one, two, module, extra, prog, newclass = None):
        
        # Search for teachers with names that start with search string
        if not request.GET.has_key('name') or request.POST.has_key('name'):
            return self.goToCore(tl)
        
        return TeacherClassRegModule.teacherlookup_logic(request, tl, one, two, module, extra, prog, newclass)
    
    @staticmethod
    def teacherlookup_logic(request, tl, one, two, module, extra, prog, newclass = None):
        limit = 10
        from esp.web.views.json import JsonResponse

        Q_teacher = Q(groups__name="Teacher")

        queryset = ESPUser.objects.filter(Q_teacher)
        
        if not request.GET.has_key('name'):
            startswith = request.POST['name']
        else:
            startswith = request.GET['name']
        s = ''
        spaces = ''
        after_comma = False
        for char in startswith:
            if char == ' ':
                if not after_comma:
                    spaces += ' '
            elif char == ',':
                s += ','
                spaces = ''
                after_comma = True
            else:
                s += spaces + char
                spaces = ''
                after_comma = False
        startswith = s
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

    class Meta:
        proxy = True

