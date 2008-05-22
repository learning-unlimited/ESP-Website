
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
from esp.program.modules.base    import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.program.modules.module_ext     import ClassRegModuleInfo
from esp.program.modules         import module_ext, manipulators
from esp.program.models          import Program, ClassSubject, ClassSection, ClassCategories, ClassImplication
from esp.datatree.models         import DataTree, GetNode
from esp.web.util                import render_to_response
from esp.middleware              import ESPError
from django                      import forms
from django.utils.datastructures import MultiValueDict
from esp.cal.models              import Event
from django.core.mail            import send_mail
from esp.miniblog.models         import Entry
from django.core.cache           import cache
from esp.db.models               import Q
from esp.users.models            import User, ESPUser
from esp.resources.models        import ResourceType, ResourceRequest
from datetime                    import timedelta

class TeacherClassRegModule(ProgramModuleObj):
    """ This program module allows teachers to register classes, and for them to modify classes/view class statuses
        as the program goes on. It is suggested, though not required, that this module is used in conjunction with
        StudentClassRegModule. Please be mindful of all the options of this module. """

    
    def extensions(self):
        """ This function gives all the extensions...that is, models that act on the join of a program and module."""
        return [('classRegInfo', module_ext.ClassRegModuleInfo)] # ClassRegModuleInfo has important information for this module


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

        if QObject:
            return {'class_approved': self.getQForUser(Q_approved_teacher),
                    'class_proposed': self.getQForUser(Q_proposed_teacher),
                    'class_rejected': self.getQForUser(Q_rejected_teacher)}

        else:
            return {'class_approved': User.objects.filter(Q_approved_teacher).distinct(),
                    'class_proposed': User.objects.filter(Q_proposed_teacher).distinct(),
                    'class_rejected': User.objects.filter(Q_rejected_teacher).distinct()}


    def teacherDesc(self):
        return {'class_approved': """Teachers teaching an approved class.""",
                'class_proposed': """Teachers teaching a class which has yet to be reviewed.""",
                'class_rejected': """Teachers teaching a rejected class."""}

    

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

        if self.classRegInfo.class_max_size:
            max_size = self.classRegInfo.class_max_size
            
        if self.classRegInfo.class_size_step:
            class_size_step = self.classRegInfo.class_size_step

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

    @needs_teacher
    @meets_deadline("/Classes/View")
    def section_students(self, request, tl, one, two, module, extra, prog):
    
        section = ClassSection.objects.filter(id=extra)
        if section.count() != 1:
            raise ESPError(False), 'Could not find that class section; please contact the webmasters.'

        return render_to_response(self.baseDir()+'class_students.html', request, (prog, tl), {'section': section[0], 'cls': section[0].parent_class})

    @needs_teacher
    @meets_deadline("/Classes/View")
    def class_students(self, request, tl, one, two, module, extra, prog):
    
        cls = ClassSubject.objects.filter(id=extra)
        if cls.count() != 1:
            raise ESPError(False), 'Could not find that class subject; please contact the webmasters.'

        return render_to_response(self.baseDir()+'class_students.html', request, (prog, tl), {'cls': cls[0]})
        

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
                data = request.POST.copy()
                data.update(request.FILES)
                form = FileUploadForm(data)
		
                
                if form.is_valid():
                    media = Media(friendly_name = form.clean_data['title'], anchor = target_class.anchor)
	            #	Append the class code on the filename
	            new_target_filename = target_class.emailcode() + '_' + form.clean_data['uploadedfile']['filename']
                    media.save_target_file_file(new_target_filename, form.clean_data['uploadedfile']['content'])
                    media.mime_type = form.clean_data['uploadedfile']['content-type']
	            media.size = len(form.clean_data['uploadedfile']['content'])
	            extension_list = form.clean_data['uploadedfile']['filename'].split('.')
	            extension_list.reverse()
	            media.file_extension = extension_list[0]
	            media.format = ''
		    
                    media.save()
	        else:
	            context_form = form
	
        context = {'cls': target_class, 'uploadform': context_form, 'module': self}
	
        return render_to_response(self.baseDir()+'class_docs.html', request, (prog, tl), context)

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
                cls.subscribe(self.user)
                self.program.teacherSubscribe(self.user)                

                # add bits for all new (and old) coteachers
                for teacher in coteachers:
                    self.program.teacherSubscribe(teacher)
                    cls.makeTeacher(teacher)
                    cls.subscribe(teacher)
                    cls.makeAdmin(teacher, self.classRegInfo.teacher_class_noedit)                    
                cls.update_cache()
                return self.goToCore(tl)


        
        return render_to_response(self.baseDir()+'coteachers.html', request, (prog, tl),{'class':cls,
                                                                                         'ajax':ajax,
                                                                                         'txtTeachers': txtTeachers,
                                                                                         'coteachers':  coteachers,
                                                                                         'conflicts':   conflictingusers})
    @meets_deadline("/Classes")
    @needs_teacher
    def editclass(self, request, tl, one, two, module, extra, prog):
        classes = ClassSubject.objects.filter(id = extra)
        if len(classes) != 1 or not self.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, (prog, tl),{})
        cls = classes[0]

        return self.makeaclass(request, tl, one, two, module, extra, prog, cls)


    @meets_deadline('/Classes')
    @needs_teacher
    def makeaclass(self, request, tl, one, two, module, extra, prog, newclass = None):
        # this is ugly...but it won't recurse and falls
        # back to @meets_deadline's behavior appropriately
        if newclass is None and not self.deadline_met():
            return meets_deadline(lambda: True)(self, request, tl, one, two, module)
        
        new_data = MultiValueDict()
        context = {'module': self}
        
        manipulator = manipulators.TeacherClassRegManipulator(self)

        if request.method == 'POST' and request.POST.has_key('class_reg_page'):
            if not self.deadline_met():
                return self.goToCore();
            
            new_data = request.POST.copy()
            errors = manipulator.get_validation_errors(new_data)
            
            # Silently drop errors from section wizard when we're not using it
            if newclass is not None:
                if prog.getSubprograms().count() > 0:
                    for subprogram in prog.getSubprograms():
                        subprogram_string = subprogram.niceName().replace(' ', '_')
                        try:
                            del errors['section_count_' + subprogram_string]
                            del errors['section_duration_' + subprogram_string]
                        except KeyError:
                            pass
            # Drop duration-validation errors if we didn't let them pick
            if len(self.getDurations()) < 1:
                try:
                    del errors['duration']
                except KeyError:
                    pass
            
            if not errors: # will succeed for errors an empty dictionary
                manipulator.do_html2python(new_data)

                newclass_isnew = False
                newclass_newmessage = True
                newclass_oldtime = timedelta() # Remember the old class duration so that we can sanity-check things later.

                if newclass is None:
                    newclass_isnew = True
                    newclass = ClassSubject()
                else:
                    if new_data['message_for_directors'] == newclass.message_for_directors:
                        newclass_newmessage = False
                    newclass_oldtime = timedelta(hours=newclass.default_section().duration)

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
                    newclass.anchor = self.program_anchor_cached().tree_create(['DummyClass'])

                    newclass.anchor.save()
                    newclass.enrollment = 0
                    newclass.save()
                    newclass.anchor.delete(True)
                
                    nodestring = newclass.category.category[:1].upper() + str(newclass.id)
                    newclass.anchor = self.program.classes_node().tree_create([nodestring])
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
                            nodestring = section.category.category[:1].upper() + str(section.id)
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
                                # create resource requests for each section
                                for res_type_id in request.POST.getlist('resources'):
                                    if res_type_id in subprogram_module.getResourceTypes():
                                        rr = ResourceRequest()
                                        rr.target = subsection
                                        rr.res_type = ResourceType.objects.get(id=res_type_id)
                                        rr.save()
                        
                        newclassimplication.member_id_ints = implied_id_ints
                        newclassimplication.save()

                #   Save resource requests (currently we do not treat global and specialized requests differently)
                #   Note that resource requests now belong to the sections
                for sec in newclass.sections.all():
                    sec.clearResourceRequests()
                    for res_type_id in request.POST.getlist('resources') + request.POST.getlist('global_resources'):
                        rr = ResourceRequest()
                        rr.target = sec
                        rr.res_type = ResourceType.objects.get(id=res_type_id)
                        rr.save()

                #   Add a component to the message for directors if the teacher is providing their own space.
                prepend_str = '*** Notice *** \n The teacher has specified that they will provide their own space for this class.  Please contact them for the size and resources the space provides (if they have not specified below) and create the appropriate resources for scheduling. \n**************\n\n'
                
                if ( new_data['has_own_space'] == 'True' ):
                    message_for_directors = prepend_str + new_data['message_for_directors']
                else:
                    message_for_directors = new_data['message_for_directors']

                # send mail to directors
                if newclass_newmessage and self.program.director_email:
                    send_mail('['+self.program.niceName()+"] Comments for " + newclass.emailcode() + ': ' + new_data.get('title'), \
                              """Teacher Registration Notification\n--------------------------------- \n\nClass Title: %s\n\nClass Description: \n%s\n\nComments to Director:\n%s\n\n""" % \
                              (new_data['title'], new_data['class_info'], message_for_directors) , \
                              ('%s <%s>' % (self.user.first_name + ' ' + self.user.last_name, self.user.email,)), \
                              [self.program.director_email], True)

                # add userbits
                if newclass_isnew:
                    newclass.makeTeacher(self.user)
                    newclass.makeAdmin(self.user, self.classRegInfo.teacher_class_noedit)
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
                new_data = newclass.__dict__
                new_data['category'] = newclass.category.id
                new_data['global_resources'] = [ req.res_type.id for req in ResourceRequest.objects.filter(target=newclass, res_type__program__isnull=True) ]
                new_data['resources'] = [ req.res_type.id for req in ResourceRequest.objects.filter(target=newclass, res_type__program__isnull=False) ]
                new_data['allow_lateness'] = newclass.allow_lateness
                new_data['has_own_space'] = False
                new_data['title'] = newclass.anchor.friendly_name
                new_data['url']   = newclass.anchor.name
                context['class'] = newclass

        context['one'] = one
        context['two'] = two
        context['form'] = forms.FormWrapper(manipulator, new_data, errors)
        
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
        
        # Don't bother showing duration selection if there isn't anything to choose from
        if len(self.getDurations()) < 1:
            context['durations'] = False
        else:
            context['durations'] = True
            
        return render_to_response(self.baseDir() + 'classedit.html', request, (prog, tl), context)


    @needs_teacher
    @meets_deadline('/Classes')    
    def teacherlookup(self, request, tl, one, two, module, extra, prog, newclass = None):
        limit = 10
        from esp.web.views.json import JsonResponse
        from esp.users.models import UserBit

        Q_teacher = Q(userbit__verb = GetNode('V/Flags/UserRole/Teacher'))

        # Search for teachers with names that start with search string
        if not request.GET.has_key('q'):
            return self.goToCore()

        queryset = User.objects.filter(Q_teacher)
        
        startswith = request.GET['q']
        parts = [x.strip() for x in startswith.split(',')]
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
        obj_list = [[user.last_name + ', ' + user.first_name + ' ('+user.username+')', user.id] for user in users]

        # Operation Complete!
        return JsonResponse(obj_list)

    def getNavBars(self):
        """ Returns a list of the dictionary to render the class catalog, if it's open """
        if super(TeacherClassRegModule, self).deadline_met('/Catalog'):
            return [{ 'link': '/learn/%s/catalog' % ( self.program.getUrlBase() ),
                      'text': '%s Catalog' % ( self.program.niceName() ) }]
        
        else:
            return []
