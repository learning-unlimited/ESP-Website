from esp.mailman import add_list_member
from esp.program.models import Program, ClassSubject, ClassSection, ClassCategories, ClassSizeRange
from esp.middleware import ESPError
from esp.program.modules.forms.teacherreg import TeacherClassRegForm
from esp.resources.forms import ResourceRequestFormSet, ResourceTypeFormSet
from esp.resources.models import ResourceType, ResourceRequest
from esp.datatree.models import GetNode
from esp.tagdict.models import Tag

from esp.dbmail.models import send_mail
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils.datastructures import SortedDict
from django.db import transaction

from datetime import timedelta, datetime
from decimal import Decimal
import simplejson as json
from django.conf import settings

def get_custom_fields():
    result = SortedDict()
    form_list_str = Tag.getTag('teacherreg_custom_forms')
    if form_list_str:
        form_cls_list = json.loads(form_list_str)
        for item in form_cls_list:
            mod = __import__('esp.program.modules.forms.teacherreg_custom', (), (), [item])
            cls = getattr(mod, item)
            for field in cls.base_fields:
                result[field] = cls.base_fields[field]
    return result

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

        self.require_teacher_has_time(user, reg_form._get_total_time_requested())

        cls = ClassSubject()
        self.attach_class_to_program(cls)
        self.make_class_happen(cls, user, reg_form, resource_formset, restype_formset)
        
        self.force_availability(user)  ## So the default DB state reflects the default form state of "all times work"

        self.send_class_mail_to_directors(cls)

        return cls

    @transaction.commit_on_success
    def editclass(self, user, reg_data, clsid, form_class=TeacherClassRegForm):
        
        reg_form, resource_formset, restype_formset = self.get_forms(reg_data, form_class=form_class)

        try:
            cls = ClassSubject.objects.get(id=int(clsid))
        except (TypeError, ClassSubject.DoesNotExist):
            raise ESPError(False), "The class you're trying to edit (ID %s) does not exist!" % (repr(clsid))

        extra_time = reg_form._get_total_time_requested() - cls.sections.count() * float(cls.duration)
        self.require_teacher_has_time(user, extra_time)

        self.make_class_happen(cls, user, reg_form, resource_formset, restype_formset, editing=True)
        
        self.force_availability(user)  ## So the default DB state reflects the default form state of "all times work"

        self.send_class_mail_to_directors(cls)

        return cls
        

    def get_forms(self, reg_data, form_class=TeacherClassRegForm):
        reg_form = form_class(self.crmi, reg_data)

        static_resource_requests = Tag.getProgramTag('static_resource_requests', self.program, )

        try:
            resource_formset = ResourceRequestFormSet(reg_data, prefix='request', static_resource_requests=static_resource_requests, )
        except ValidationError:
            resource_formset = None

        try:
            restype_formset = ResourceTypeFormSet(reg_data, prefix='restype')
        except ValidationError:
            restype_formset = None
            
        if not reg_form.is_valid() or (resource_formset and not resource_formset.is_valid()) or (restype_formset and not restype_formset.is_valid()):
            raise ClassCreationValidationError, (reg_form, resource_formset, restype_formset, "Invalid form data.  Please make sure you are using the official registration form, on esp.mit.edu.  If you are, please let us know how you got this error.")

        return reg_form, resource_formset, restype_formset
    
    def make_class_happen(self, cls, user, reg_form, resource_formset, restype_formset, editing=False):
        anchor_modified = self.set_class_data(cls, reg_form)
        self.update_class_sections(cls, int(reg_form.cleaned_data['num_sections']))

        #   If someone is editing the class, we assume they don't want to be
        #   added as a teacher if they aren't already one.
        if anchor_modified:
            cls.save()
            for teacher in cls.teachers.all():
                self.associate_teacher_with_class(cls, teacher)
            if not editing:
                self.associate_teacher_with_class(cls, user)
        self.add_rsrc_requests_to_class(cls, resource_formset, restype_formset)

        #   If someone is editing the class who isn't teaching it, don't unapprove it.
        if user in cls.teachers.all():
            cls.propose()
        
    def set_class_data(self, cls, reg_form):
        custom_fields = get_custom_fields()
        custom_data = {}
    
        for k, v in reg_form.cleaned_data.items():
            if k in custom_fields:
                custom_data[k] = v
            elif k not in ('category', 'resources', 'viable_times', 'optimal_class_size_range', 'allowable_class_size_ranges', 'title') and k[:8] is not 'section_':
                cls.__dict__[k] = v
        
        cls.custom_form_data = custom_data

        if hasattr(cls, 'duration'):
            cls.duration = Decimal(cls.duration)
            
        cls.category = ClassCategories.objects.get(id=reg_form.cleaned_data['category'])

        if 'optimal_class_size_range' in reg_form.cleaned_data and reg_form.cleaned_data['optimal_class_size_range']:
            cls.optimal_class_size_range = ClassSizeRange.objects.get(id=reg_form.cleaned_data['optimal_class_size_range'])

        #   Set title of class explicitly
        cls.save()
        anchor_modified = self.update_class_anchorname(cls, reg_form.cleaned_data['title'])

        if 'allowable_class_size_ranges' in reg_form.cleaned_data and reg_form.cleaned_data['allowable_class_size_ranges']:
            cls.allowable_class_size_ranges = ClassSizeRange.objects.filter(id__in=reg_form.cleaned_data['allowable_class_size_ranges'])
            cls.save()
            
        return anchor_modified

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

    def update_class_anchorname(self, cls, title):
        nodestring = cls.emailcode()
        if cls.anchor and nodestring == cls.anchor.name:
            anchor_modified = False
        else:
            anchor_modified = True
        cls.anchor = self.program.classes_node().tree_create([nodestring])
        cls.anchor.tree_create(['TeacherEmail'])  ## Just to make sure it's there
        cls.anchor.friendly_name = title
        cls.anchor.save()
        return anchor_modified

    def associate_teacher_with_class(self, cls, user):
        self.add_teacher_to_program_mailinglist(user)

        cls.makeTeacher(user)
        cls.makeAdmin(user, self.crmi.teacher_class_noedit)
        cls.subscribe(user)
        self.program.teacherSubscribe(user)

    def force_availability(self, user):
        if len(user.getAvailableTimes(self.program)) == 0:
            for ts in self.program.getTimeSlots():
                user.addAvailableTime(self.program, ts)
            note = 'Availability was set automatically by the server in order to clear space for a newly registered class.'
            self.send_availability_email(user, note)

    def send_availability_email(self, teacher, note=None):
        timeslots = teacher.getAvailableTimes(self.program, ignore_classes=True)
        email_title = 'Availability for %s: %s' % (self.program.niceName(), teacher.name())
        email_from = '%s Registration System <server@%s>' % (self.program.anchor.parent.name, settings.EMAIL_HOST_SENDER)
        email_context = {'teacher': teacher,
                         'timeslots': timeslots,
                         'program': self.program,
                         'curtime': datetime.now(),
                         'note': note}
        email_contents = render_to_string('program/modules/availabilitymodule/update_email.txt', email_context)
        email_to = ['%s <%s>' % (teacher.name(), teacher.email)]
        send_mail(email_title, email_contents, email_from, email_to, False)

    def teacher_has_time(self, user, hours):
        return (user.getTaughtTime(self.program, include_scheduled=True) + timedelta(hours=hours) \
                <= self.program.total_duration())

    def require_teacher_has_time(self, user, hours):
        if not self.teacher_has_time(user, hours):
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
            return resform.cleaned_data['desired_value']
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


    def generate_director_mail_context(self, cls):
        new_data = cls.__dict__
        mail_ctxt = dict(new_data.iteritems())
        
        mail_ctxt['title'] = cls.title()
        mail_ctxt['one'] = cls.parent_program.anchor.parent.name
        mail_ctxt['two'] = cls.parent_program.anchor.name
        mail_ctxt['DEFAULT_HOST'] = settings.DEFAULT_HOST
        
        # Make some of the fields in new_data nicer for viewing.
        mail_ctxt['category'] = ClassCategories.objects.get(id=new_data['category_id']).category
        #mail_ctxt['global_resources'] = ResourceType.objects.filter(id__in=new_data['global_resources'])
        mail_ctxt['global_resources'] = cls.get_sections()[0].getResourceRequests()

        # Optimal and allowable class size ranges.
        if new_data.has_key('optimal_class_size_range_id') and (new_data['optimal_class_size_range_id'] is not None):
            opt_range = ClassSizeRange.objects.get(id=new_data['optimal_class_size_range_id'])
            mail_ctxt['optimal_class_size_range'] = str(opt_range.range_min) + "-" + str(opt_range.range_max)
        else:
            mail_ctxt['optimal_class_size_range'] = ''
        try:
            mail_ctxt['allowable_class_size_ranges'] = cls.allowable_class_size_ranges.all()
        except:
            # If the allowable_class_size_ranges field doesn't exist, just don't do anything.
            pass
        
        mail_ctxt['teachers'] = []
        for teacher in cls.teachers.all():
            teacher_ctxt = {'teacher': teacher}
            # Provide information about whether or not teacher's from MIT.
            last_profile = teacher.getLastProfile()
            if last_profile.teacher_info != None:
                teacher_ctxt['from_here'] = last_profile.teacher_info.from_here
                teacher_ctxt['college'] = last_profile.teacher_info.college
            else: # This teacher never filled out their teacher profile!
                teacher_ctxt['from_here'] = "[Teacher hasn't filled out teacher profile!]"
                teacher_ctxt['college'] = "[Teacher hasn't filled out teacher profile!]"

            # Get a list of the programs this person has taught for in the past, if any.
            teacher_ctxt['taught_programs'] = u', '.join([prog.niceName() for prog in teacher.getTaughtPrograms().order_by('pk').exclude(id=self.program.id)])
            mail_ctxt['teachers'].append(teacher_ctxt)
        return mail_ctxt


    def send_class_mail_to_directors(self, cls):
        mail_ctxt = self.generate_director_mail_context(cls)
        
        recipients = [teacher.email for teacher in cls.teachers.all()]
        if recipients:
            send_mail('['+self.program.niceName()+"] Comments for " + cls.emailcode() + ': ' + cls.title(), \
                      render_to_string('program/modules/teacherclassregmodule/classreg_email', mail_ctxt) , \
                      ('%s Class Registration <%s>' % (self.program.anchor.parent.name, self.program.director_email)), \
                      recipients, False)

        if self.program.director_email:
            mail_ctxt['admin'] = True
            send_mail('['+self.program.niceName()+"] Comments for " + cls.emailcode() + ': ' + cls.title(), \
                      render_to_string('program/modules/teacherclassregmodule/classreg_email', mail_ctxt) , \
                      ('%s Class Registration <%s>' % (self.program.anchor.parent.name, self.program.director_email)), \
                      [self.program.director_email], False)
