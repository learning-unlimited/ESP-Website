
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
from esp.program.modules.base    import ProgramModuleObj, needs_teacher, meets_deadline, main_call, aux_call
from esp.program.modules.module_ext     import ClassRegModuleInfo
from esp.program.modules         import module_ext
from esp.program.modules.forms.teacherreg   import TeacherClassRegForm
from esp.program.models          import ClassSubject, ClassSection, ClassCategories, ClassImplication
from esp.datatree.models import *
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

        full_classes = [x.anchor for x in self.program.classes().filter(status__gt=0) if x.is_nearly_full()]
        Q_full_teacher = Q(userbit__qsc__in=full_classes) & Q_isteacher

        if QObject:
            return {'class_approved': self.getQForUser(Q_approved_teacher),
                    'class_proposed': self.getQForUser(Q_proposed_teacher),
                    'class_rejected': self.getQForUser(Q_rejected_teacher),
                    'class_full': self.getQForUser(Q_full_teacher)}

        else:
            return {'class_approved': User.objects.filter(Q_approved_teacher).distinct(),
                    'class_proposed': User.objects.filter(Q_proposed_teacher).distinct(),
                    'class_rejected': User.objects.filter(Q_rejected_teacher).distinct(),
                    'class_full': User.objects.filter(Q_full_teacher).distinct()}


    def teacherDesc(self):
        return {'class_approved': """Teachers teaching an approved class.""",
                'class_proposed': """Teachers teaching a class which has yet to be reviewed.""",
                'class_rejected': """Teachers teaching a rejected class.""",
                'class_full': """Teachers teaching a nearly-full class."""}

    

    def deadline_met(self):
        if self.user.isAdmin(self.program):
            return True
        
        tmpModule = ProgramModuleObj()
        tmpModule.__dict__ = self.__dict__
        return tmpModule.deadline_met('/Classes')
    
    def clslist(self):
        return [cls for cls in self.user.getTaughtClasses()
                if cls.parent_program.id == self.program.id ]

    def getClassSizes(self):
        min_size, max_size, class_size_step = (0, 200, 10)

        if self.class_max_size:
            max_size = self.class_max_size
            
        if self.class_size_step:
            class_size_step = self.class_size_step

        ret_range = range(0, 23) + [30, 35, 40, 150]
        ret_range = filter(lambda x: ((x >= min_size) and (x <= max_size)), ret_range)

        return ret_range

    def getClassGrades(self):
        min_grade, max_grade = (6, 12)
        if self.program.grade_min:
            min_grade = self.program.grade_min
        if self.program.grade_max:
            max_grade = self.program.grade_max

        return range(min_grade, max_grade+1)

    def getTimes(self):
        times = self.program.getTimeSlots()
        return [(str(x.id),x.short_description) for x in times]

    def getDurations(self):
        return self.program.getDurations()

    def getResources(self):
        resources = self.program.getResources()
        return [(str(x.id), x.name) for x in resources]
   
    def getResourceTypes(self, is_global=None):
        #   Get a list of all resource types, excluding the fundamental ones.
        base_types = self.program.getResourceTypes().filter(priority_default__gt=0)
        
        if is_global is True:
            res_types = base_types.filter(program__isnull=True)
        elif is_global is False:
            res_types = base_types.filter(program__isnull=False)
        else:
            res_types = base_types
            
        return [(str(x.id), x.name) for x in res_types]

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
    @meets_deadline("/Classes/View")
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
                        verb = DataTree.get_by_uri('V/Flags/Registration/' + verb_name, create=True)
                        other_bits = sec.getRegBits(student).filter(verb__name__in=['Enrolled', 'Rejected'])
                        found = False
                        for bit in other_bits:
                            if not found and bit.verb == verb:
                                found = True
                            else:
                                bit.expire()
                            #   result_strs.append('Expired: %s' % bit)
                        if not found:
                            new_bit = UserBit(user=student, verb=verb, qsc=sec.anchor)
                            new_bit.save()
                        #   result_strs.append('Created: %s' % new_bit)
                        
        #   Jazz up this information a little
        for student in students_list:
            uri_base = 'V/Flags/Registration/'
            uri_start = len(uri_base)
            bits = sec.getRegBits(student)
            student.bits = [bit.verb.get_uri()[uri_start:] for bit in bits]
            student.app = student.getApplication(self.program, False)
            student.other_classes = [(sec2, [bit.verb.get_uri()[uri_start:] for bit in sec2.getRegBits(student)]) for sec2 in student.getSections(self.program).exclude(id=sec.id)]
            prereg_bits = bits.exclude(verb__name__in=['Enrolled', 'Rejected'])
            if prereg_bits.count() != 0:
               student.added_class = prereg_bits[0].startdate
            if bits.filter(verb__name='Enrolled').count() > 0:
                student.enrolled = True
            elif bits.filter(verb__name='Rejected').count() > 0:
                student.rejected = True

        return render_to_response(self.baseDir()+'select_students.html', request, (prog, tl), {'prog': prog, 'sec': sec, 'students_list': students_list})

        
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
        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) != 1 or not self.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, (prog, tl),{})
        cls = classes[0]

        return self.makeaclass(request, tl, one, two, module, extra, prog, cls)

    @aux_call
    @meets_deadline('/Classes')
    @needs_teacher
    def makeaclass(self, request, tl, one, two, module, extra, prog, newclass = None):
        # this is ugly...but it won't recurse and falls
        # back to @meets_deadline's behavior appropriately
        if newclass is None and not self.deadline_met():
            return meets_deadline(lambda: True)(self, request, tl, one, two, module)
        
        new_data = MultiValueDict()
        context = {'module': self}
        
        if request.method == 'POST' and request.POST.has_key('class_reg_page'):
            if not self.deadline_met():
                return self.goToCore(tl)
            
            reg_form = TeacherClassRegForm(self, request.POST)
            resource_formset = ResourceRequestFormSet(request.POST, prefix='request')
            restype_formset = ResourceTypeFormSet(request.POST, prefix='restype')
            # Silently drop errors from section wizard when we're not using it
            if reg_form.is_valid() and resource_formset.is_valid() and restype_formset.is_valid():
                new_data = reg_form.cleaned_data
                
                # Some defaults
                newclass_isnew = False
                newclass_newmessage = True
                newclass_oldtime = timedelta() # Remember the old class duration so that we can sanity-check things later.

                if newclass is None:
                    newclass_isnew = True
                    newclass = ClassSubject()
                else:
                    if new_data['message_for_directors'] == newclass.message_for_directors:
                        newclass_newmessage = False
                    newclass_oldtime = timedelta(hours=float(newclass.default_section().duration))

                for k, v in new_data.items():
                    if k not in ('category', 'resources', 'viable_times') and k[:8] is not 'section_':
                        newclass.__dict__[k] = v
                
                newclass.category = ClassCategories.objects.get(id=new_data['category'])

                #   Allow for no selected duration (directors will assign one to default value)
                if new_data['duration'] == '':
                    new_duration = 0.0
                else:
                    try:
                        new_duration = float(new_data['duration'])
                    except:
                        new_duration = 0.0

                # Makes sure the program has time for this class
                # If the time you're already teaching plus the time of the class you propose exceeds the program's total time, fail.
                # The newclass_oldtime term balances things out if this isn't actually a new class.
                self.user = ESPUser(self.user)
                if self.user.getTaughtTime(prog, include_scheduled=True) + timedelta(hours=new_duration) > self.program.total_duration() + newclass_oldtime:
                    raise ESPError(False), 'We love you too!  However, you attempted to register for more hours of class than we have in the program.  Please go back to the class editing page and reduce the duration, or remove or shorten other classes to make room for this one.'

                # datatree maintenance
                if newclass_isnew:
                    newclass.parent_program = self.program
                    newclass.anchor = self.program.classes_node()
                    newclass.save()
                
                    nodestring = newclass.category.symbol + str(newclass.id)
                    newclass.anchor = newclass.anchor.tree_create([nodestring])
                    newclass.anchor.tree_create(['TeacherEmail'])
                    
                newclass.anchor.friendly_name = newclass.title
                newclass.anchor.save()
                newclass.save()
                
                #   Give the class the appropriate number of sections as specified by the teacher.
                num_sections = int(new_data['num_sections'])
                section_list = list( newclass.sections.all() )
                for i in range(newclass.sections.count(), num_sections):
                    section_list.append(newclass.add_section(duration=new_duration))

                # If the teacher wants to decrease the number of sections that they're teaching
                if num_sections < len(section_list):
                    for class_section in section_list[num_sections:]:
                        class_section.delete()
                        
                # Set duration of sections
                for section in newclass.sections.all():
                    section.duration = newclass.duration
                    section.save()

                # create classes in subprograms -- the work for this should probably be farmed out to another function
                if newclass_isnew:
                    if prog.getSubprograms().count() > 0:
                        # copy class information to section data
                        section_data = {}
                        for k, v in new_data.items():
                            if k not in ('category', 'resources', 'viable_times') and k[:8] is not 'section_':
                                section_data[k] = v
                        
                        # prepare a ClassImplication, to be ready for student reg
                        newclassimplication = ClassImplication()
                        newclassimplication.cls = newclass
                        newclassimplication.operation = 'OR'
                        implied_id_ints = []
                        
                        for subprogram in prog.getSubprograms():
                            # prepare some information 
                            subprogram_string = subprogram.niceName().replace(' ', '_')
                            try:
                                subprogram_module = ProgramModuleObj.getFromProgModule(subprogram, self.module)
                                subprogram_classreginfo = ClassRegModuleInfo.objects.get(module__program=subprogram)
                            except:
                                continue
                            
                            # modify data as appropriate to subprogram
                            if new_data['section_duration_' + subprogram_string] == '':
                                section_data['duration'] = 0.0
                            else:
                                try:
                                    section_data['duration'] = float(new_data['section_duration_' + subprogram_string])
                                except:
                                    section_data['duration'] = 0.0
                                    
                            section_count = 1
                            try:
                                section_count = int(new_data['section_count_' + subprogram_string])
                            except:
                                pass
                                    
                            # If the time of the proposed sections plus the time you're already teaching for this program exceed the program's total time, fail.
                            if timedelta(hours = section_data['duration'] * section_count) + self.user.getTaughtTime(subprogram, include_scheduled=True) > subprogram.total_duration():
                                # Delete new class--prevent teacherless classes from showing up when we throw an error right here.
                                # If there's more than one subprogram, this won't avoid orphaned sections and classimplications.
                                newclass.delete()
                                raise ESPError(False), 'We love you too!  However, you attempted to create too many sections of your class.  There is not enough time in the program to support those sections.  Please go back to the class editing page and reduce the length or quantity of sections.'
                                    
                            section_data['parent_program_id'] = subprogram.id
                            
                            # make a new class and copy the section data into it
                            section = ClassSubject()
                            for k, v in section_data.items():
                                section.__dict__[k] = v
                            section.category = ClassCategories.objects.get(id=new_data['category'])
                            
                            # get an id
                            section.anchor = self.program_anchor_cached().tree_create(['DummyClass'])
                            section.anchor.save()
                            section.save()
                            section.anchor.delete(True)
                            
                            # set up the class's actual location on the data tree
                            nodestring = section.category.symbol + str(section.id)
                            section.anchor = subprogram.classes_node().tree_create([nodestring])
                            section.anchor.tree_create(['TeacherEmail'])
                            section.anchor.friendly_name = section.title
                            section.anchor.save()
                            section.save()
                            
                            # create the userbits for the section
                            section.makeTeacher(self.user)
                            section.makeAdmin(self.user, subprogram_classreginfo.teacher_class_noedit)
                            section.subscribe(self.user)
                            subprogram.teacherSubscribe(self.user)
                            section.propose()

                            # update class implication list
                            implied_id_ints.append( section.id )
                            
                            section.update_cache()
                            for i in range(0, section_count):
                                subsection = section.add_section(duration=section_data['duration'])
                                #   Create resource requests for each section
                                #   Create new resource types (with one request per type) if desired
                                for resform in resource_formset.forms:
                                    rr = ResourceRequest()
                                    rr.target = subsection
                                    rr.res_type = resform.cleaned_data['resource_type']
                                    rr.desired_value = resform.cleaned_data['desired_value']
                                    rr.save()
                                for resform in restype_formset.forms:
                                    #   Save new types; handle imperfect validation
                                    if len(resform.cleaned_data['name']) > 0:
                                        rt = ResourceType.get_or_create(resform.cleaned_data['name'])
                                        rt.choices = ['Yes']
                                        rt.save()
                                        rr = ResourceRequest()
                                        rr.target = subsection
                                        rr.res_type = rt
                                        rr.desired_value = 'Yes'
                                        rr.save()
                        
                        newclassimplication.member_id_ints = implied_id_ints
                        newclassimplication.save()

                #   Save resource requests (currently we do not treat global and specialized requests differently)
                #   Note that resource requests now belong to the sections
                for sec in newclass.sections.all():
                    sec.clearResourceRequests()
                    for resform in resource_formset.forms:
                        rr = ResourceRequest()
                        rr.target = sec
                        rr.res_type = resform.cleaned_data['resource_type']
                        rr.desired_value = resform.cleaned_data['desired_value']
                        rr.save()
                    for resform in restype_formset.forms:
                        #   Save new types; handle imperfect validation
                        if len(resform.cleaned_data['name']) > 0:
                            rt = ResourceType.get_or_create(resform.cleaned_data['name'])
                            rt.choices = ['Yes']
                            rt.save()
                            rr = ResourceRequest()
                            rr.target = sec
                            rr.res_type = rt
                            rr.desired_value = 'Yes'
                            rr.save()

                
                mail_ctxt = dict(new_data) # context for email sent to directors

                # Make some of the fields in new_data nicer for viewing.
                mail_ctxt['category'] = ClassCategories.objects.get(id=new_data['category']).category
                mail_ctxt['global_resources'] = ResourceType.objects.filter(id__in=new_data['global_resources'])

                # send mail to directors
                if newclass_newmessage and self.program.director_email:
                    send_mail('['+self.program.niceName()+"] Comments for " + newclass.emailcode() + ': ' + new_data.get('title'), \
                              render_to_string(self.baseDir() + 'classreg_email', mail_ctxt) , \
                              ('%s <%s>' % (self.user.first_name + ' ' + self.user.last_name, self.user.email,)), \
                              [self.program.director_email], True)

                # add userbits
                if newclass_isnew:
                    newclass.makeTeacher(self.user)
                    newclass.makeAdmin(self.user, self.teacher_class_noedit)
                    newclass.subscribe(self.user)
                    self.program.teacherSubscribe(self.user)
                    newclass.propose()
                else:
                    if self.user.isAdmin(self.program):

                        newclass.update_cache()
                        return self.goToCore('manage')

                #cache this result
                newclass.update_cache()                
                #   This line is for testing only. -Michael P
                #   return render_to_response(self.baseDir() + 'classedit.html', request, (prog, tl), context)
                return self.goToCore(tl)
        else:
            errors = {}
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
                context['class'] = newclass
                reg_form = TeacherClassRegForm(self, current_data)
                
                #   Todo...
                ds = newclass.default_section()
                class_requests = ResourceRequest.objects.filter(target=ds)
                resource_formset = ResourceRequestFormSet(initial=[{'resource_type': x.res_type, 'desired_value': x.desired_value} for x in class_requests], resource_type=[x.res_type for x in class_requests], prefix='request')
                restype_formset = ResourceTypeFormSet(initial=[], prefix='restype')
            else:
                reg_form = TeacherClassRegForm(self)
                type_labels = ['Classroom', 'A/V']
                #   Provide initial forms: a request for each provided type, but no requests for new types.
                resource_formset = ResourceRequestFormSet(initial=[{} for x in type_labels], resource_type=[ResourceType.get_or_create(x) for x in type_labels], prefix='request')
                restype_formset = ResourceTypeFormSet(initial=[], prefix='restype')

        context['one'] = one
        context['two'] = two
        context['form'] = reg_form
        context['formset'] = resource_formset
        context['restype_formset'] = restype_formset
        context['resource_types'] = ResourceType.objects.all()
        
        if newclass is None:
            context['addoredit'] = 'Add'
            if prog.getSubprograms().count() > 0:
                context['subprograms'] = []
                for subprogram in prog.getSubprograms():
                    subprogram_string = subprogram.niceName().replace(' ', '_')
                    context['subprograms'].append({ 'name': subprogram.niceName(), \
                                                    'id_string': subprogram_string, \
                                                    'section_count_field': context['form']['section_count_' + subprogram_string], \
                                                    'section_duration_field': context['form']['section_duration_' + subprogram_string]})
        else:
            context['addoredit'] = 'Edit'
            
        return render_to_response(self.baseDir() + 'classedit.html', request, (prog, tl), context)


    @aux_call
    @needs_teacher
#    @meets_deadline('/Classes')    
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

        # Operation Complete!
        json_dict = {
            "label": "name",
            "identifier": "id",
            "items": obj_list
        }
        
        #return JsonResponse(json_dict)
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
