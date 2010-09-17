from esp.mailman import add_list_member
from esp.program.models import Program, ClassSubject, ClassSection, ClassCategories, ClassSizeRange
from esp.middleware import ESPError
from esp.program.modules.forms.teacherreg import TeacherClassRegForm
from esp.resources.forms import ResourceRequestFormSet, ResourceTypeFormSet
from esp.resources.models import ResourceType, ResourceRequest
from esp.datatree.models import GetNode

from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.db import transaction

from datetime import timedelta
from decimal import Decimal

class ClassCreationValidationError(Exception):
    def __init__(self, reg_form, resource_formset, restype_formset, error_msg):
        self.reg_form = reg_form
        self.resource_formset = resource_formset
        self.restype_formset = restype_formset
        super(ClassCreationValidationError, self).__init__(error_msg)

class ClassCreationController(object):
    def __init__(self, prog):
        self.program = prog
        self.crmi = prog.getModuleExtension('ClassRegModuleInfo')

    @transaction.commit_on_success
    def makeaclass(self, user, reg_data, form_class=TeacherClassRegForm):

        reg_form, resource_formset, restype_formset = self.get_forms(reg_data, form_class=form_class)

        cls = ClassSubject()
        self.attach_class_to_program(cls)
        self.make_class_happen(cls, user, reg_form, resource_formset, restype_formset)
        
        self.force_availability(user)  ## So the default DB state reflects the default form state of "all times work"

        self.require_teacher_has_time_for_class(user, cls)

        self.send_class_mail_to_directors(cls, user)

        return cls

    @transaction.commit_on_success
    def editclass(self, user, reg_data, clsid, form_class=TeacherClassRegForm):
        
        reg_form, resource_formset, restype_formset = self.get_forms(reg_data, form_class=form_class)

        try:
            cls = ClassSubject.objects.get(id=int(clsid))
        except (TypeError, ClassSubject.DoesNotExist):
            raise ESPError(False), "The class you're trying to edit (ID %s) does not exist!" % (repr(clsid))
        
        self.make_class_happen(cls, user, reg_form, resource_formset, restype_formset)
        
        self.force_availability(user)  ## So the default DB state reflects the default form state of "all times work"

        self.require_teacher_has_time_for_class(user, cls)

        self.send_class_mail_to_directors(cls, user)

        return cls
        

    def get_forms(self, reg_data, form_class=TeacherClassRegForm):
        reg_form = form_class(self.crmi, reg_data)

        try:
            resource_formset = ResourceRequestFormSet(reg_data, prefix='request')
        except ValidationError:
            resource_formset = None

        try:
            restype_formset = ResourceTypeFormSet(reg_data, prefix='restype')
        except ValidationError:
            restype_formset = None
            
        if not reg_form.is_valid() or (resource_formset and not resource_formset.is_valid()) or (restype_formset and not restype_formset.is_valid()):
            print "classreg get_forms", reg_form.errors, "\n", resource_formset.errors, "\n", restype_formset.errors
            raise ClassCreationValidationError, (reg_form, resource_formset, restype_formset, "Invalid form data.  Please make sure you are using the official registration form, on esp.mit.edu.  If you are, please let us know how you got this error.")

        return reg_form, resource_formset, restype_formset
    
    def make_class_happen(self, cls, user, reg_form, resource_formset, restype_formset):
        self.set_class_data(cls, reg_form)
        self.update_class_sections(cls, int(reg_form.cleaned_data['num_sections']))
        self.associate_teacher_with_class(cls, user)
        self.add_rsrc_requests_to_class(cls, resource_formset, restype_formset)
        cls.propose()
        cls.update_cache()

    def set_class_data(self, cls, reg_form):
        for k, v in reg_form.cleaned_data.items():
            if k not in ('category', 'resources', 'viable_times', 'optimal_class_size_range', 'allowable_class_size_ranges') and k[:8] is not 'section_':
                cls.__dict__[k] = v

        if hasattr(cls, 'duration'):
            cls.duration = Decimal(cls.duration)
            
        cls.category = ClassCategories.objects.get(id=reg_form.cleaned_data['category'])

        if 'optimal_class_size_range' in reg_form.cleaned_data and reg_form.cleaned_data['optimal_class_size_range']:
            cls.optimal_class_size_range = ClassSizeRange.objects.get(id=reg_form.cleaned_data['optimal_class_size_range'])

        if cls.anchor.friendly_name != cls.title:
            self.update_class_anchorname(cls)

        cls.save()

        if 'allowable_class_size_ranges' in reg_form.cleaned_data and reg_form.cleaned_data['allowable_class_size_ranges']:
            cls.allowable_class_size_ranges = ClassSizeRange.objects.filter(id__in=reg_form.cleaned_data['allowable_class_size_ranges'])
            cls.save()

    def update_class_sections(self, cls, num_sections):
        #   Give the class the appropriate number of sections as specified by the teacher.
        section_list = list( cls.sections.all() )
        for i in range(len(section_list), num_sections):
            section_list.append(cls.add_section(duration=cls.duration))

        # If the teacher wants to decrease the number of sections that they're teaching
        if num_sections < len(section_list):
            for class_section in section_list[num_sections:]:
                class_section.delete()
                        
        # Set duration of sections
        cls.sections.update(duration = cls.duration)

    def attach_class_to_program(self, cls):        
        cls.parent_program = self.program
        cls.anchor = self.program.classes_node()

    def update_class_anchorname(self, cls):
        nodestring = cls.category.symbol + str(cls.id)
        cls.anchor = self.program.classes_node().tree_create([nodestring])
        cls.anchor.tree_create(['TeacherEmail'])  ## Just to make sure it's there
        cls.anchor.friendly_name = cls.title
        cls.anchor.save()

    def associate_teacher_with_class(self, cls, user):
        self.add_teacher_to_program_mailinglist(user)

        cls.makeTeacher(user)
        cls.makeAdmin(user, self.crmi.teacher_class_noedit)
        cls.subscribe(user)
        self.program.teacherSubscribe(user)

    def force_availability(self, user):
        if user.getAvailableTimes(self.program).count() == 0:
            for ts in self.program.getTimeSlots():
                user.addAvailableTime(self.program, ts)

    def teacher_has_time_for_class(self, user, cls, cls_old_time = timedelta(0)):
        return (user.getTaughtTime(self.program, include_scheduled=True) + timedelta(hours=float(cls.duration)) \
                <= self.program.total_duration() + cls_old_time)

    def require_teacher_has_time_for_class(self, user, cls, cls_old_time = timedelta(0)):
        if not self.teacher_has_time_for_class(user, cls, cls_old_time):
            raise ESPError(False), 'We love you too!  However, you attempted to register for more hours of class than we have in the program.  Please go back to the class editing page and reduce the duration, or remove or shorten other classes to make room for this one.'

    def add_teacher_to_program_mailinglist(self, user):
        add_list_member("%s_%s-teachers" % (self.program.anchor.parent.name, self.program.anchor.name), user)

    def add_rsrc_requests_to_class(self, cls, resource_formset, restype_formset):
        for sec in cls.get_sections():
            sec.clearResourceRequests()
            if resource_formset:
                for resform in resource_formset.forms:
                    self.import_resource_formset(sec, resform)
            if restype_formset:
                for resform in restype_formset.forms:
                    #   Save new types; handle imperfect validation
                    if len(resform.cleaned_data['name']) > 0:
                        self.import_restype_formset(self, sec, resform)
                    
    def import_resource_formset(self, sec, resform):
        if isinstance(resform.cleaned_data['desired_value'], list):
            for val in resform.cleaned_data['desired_value']:
                rr = ResourceRequest()
                rr.target = sec
                rr.res_type = resform.cleaned_data['resource_type']
                rr.desired_value = val
                rr.save()
        else:
            rr = ResourceRequest()
            rr.target = sec
            rr.res_type = resform.cleaned_data['resource_type']
            rr.desired_value = resform.cleaned_data['desired_value']
            rr.save()
        return rr

    def import_restype_formset(self, sec, resform):
        rt, created = ResourceType.get_or_create(resform.cleaned_data['name'])
        rt.choices = ['Yes']
        rt.save()
        rr = ResourceRequest()
        rr.target = sec
        rr.res_type = rt
        rr.desired_value = 'Yes'
        rr.save()
        return (rt, rr)


    def generate_director_mail_context(self, cls, user):
        new_data = cls.__dict__
        mail_ctxt = dict(new_data.iteritems())

        
        # Make some of the fields in new_data nicer for viewing.
        mail_ctxt['category'] = ClassCategories.objects.get(id=new_data['category_id']).category
        mail_ctxt['global_resources'] = ResourceType.objects.filter(id__in=new_data['global_resources'])
        
        # Provide information about whether or not teacher's from MIT.
        last_profile = user.getLastProfile()
        if last_profile.teacher_info != None:
            mail_ctxt['from_here'] = last_profile.teacher_info.from_here
            mail_ctxt['college'] = last_profile.teacher_info.college
        else: # This teacher never filled out their teacher profile!
            mail_ctxt['from_here'] = "[Teacher hasn't filled out teacher profile!]"
            mail_ctxt['college'] = "[Teacher hasn't filled out teacher profile!]"

        # Get a list of the programs this person has taught for in the past, if any.
        taught_programs = Program.objects.filter(anchor__child_set__child_set__userbit_qsc__user=user, \
                                                 anchor__child_set__child_set__userbit_qsc__verb=GetNode('V/Flags/Registration/Teacher'), \
                                                 anchor__child_set__child_set__userbit_qsc__qsc__classsubject__status=10).distinct().exclude(id=self.program.id)
        mail_ctxt['taught_programs'] = taught_programs

        return mail_ctxt


    def send_class_mail_to_directors(self, cls, user):
        if self.program.director_email:
            mail_ctxt = self.generate_director_mail_context(cls, user)
            send_mail('['+self.program.niceName()+"] Comments for " + cls.emailcode() + ': ' + cls.title, \
                      render_to_string('program/modules/teacherclassregmodule/classreg_email', mail_ctxt) , \
                      ('%s <%s>' % (user.first_name + ' ' + user.last_name, user.email,)), \
                      [self.program.director_email], True)
