from esp.mailman import add_list_member
from esp.program.models import Program, ClassSubject, ClassSection, ClassCategories, ClassSizeRange, Event
from esp.program.class_status import ClassStatus
from esp.middleware import ESPError
from esp.program.modules.forms.teacherreg import TeacherClassRegForm, TeacherOpenClassRegForm
from esp.resources.forms import ResourceRequestFormSet
from esp.resources.models import ResourceType, ResourceRequest
from esp.tagdict.models import Tag
from esp.users.models import ESPUser

from esp.dbmail.models import send_mail
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from collections import OrderedDict
from django.db import transaction

from datetime import timedelta, datetime
from decimal import Decimal
import json
from django.conf import settings

def get_custom_fields():
    result = OrderedDict()
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
    def __init__(self, reg_form, resource_formset, error_msg):
        self.reg_form = reg_form
        self.resource_formset = resource_formset
        super().__init__(error_msg)

class ClassCreationController(object):
    def __init__(self, prog):
        self.program = prog
        self.crmi = prog.classregmoduleinfo

    @transaction.atomic
    def makeaclass(self, user, reg_data, form_class=TeacherClassRegForm):

        reg_form, resource_formset = self.get_forms(reg_data, form_class=form_class)

        if form_class == TeacherOpenClassRegForm:
            reg_form.cleaned_data['grade_min'] = self.program.grade_min
            reg_form.cleaned_data['grade_max'] = self.program.grade_max

        self.require_teacher_has_time(user, user, reg_form._get_total_time_requested())

        cls = ClassSubject()
        self.attach_class_to_program(cls)
        self.make_class_happen(cls, user, reg_form, resource_formset)

        self.force_availability(user)  ## So the default DB state reflects the default form state of "all times work"

        self.send_class_mail_to_directors(cls)

        return cls

    @transaction.atomic
    def editclass(self, current_user, reg_data, clsid, form_class=TeacherClassRegForm):

        reg_form, resource_formset = self.get_forms(reg_data, form_class=form_class)

        try:
            cls = ClassSubject.objects.get(id=int(clsid))
        except (TypeError, ClassSubject.DoesNotExist):
            raise ESPError(f"The class you're trying to edit (ID {repr(clsid)}) does not exist!", log=False)

        extra_time = reg_form._get_total_time_requested() - cls.sections.count() * float(cls.duration)
        for teacher in cls.get_teachers():
            self.require_teacher_has_time(teacher, current_user, extra_time)

        self.make_class_happen(cls, None, reg_form, resource_formset, editing=True)

        self.send_class_mail_to_directors(cls, False)

        return cls

    @transaction.atomic
    def save_class_draft(self, user, reg_data, clsid=None, action='create'):
        """
        Save a class as a draft without validation.
        Handles ALL fields from ClassSubject model systematically.
        """
        
        # Create or get class
        if action in ['create', 'createopenclass']:
            # Check if user already has a draft for this program
            existing_draft = ClassSubject.objects.filter(
                parent_program=self.program,
                teachers=user,
                status=ClassStatus.DRAFT
            ).first()
            
            if existing_draft:
                cls = existing_draft
            else:
                cls = ClassSubject()
                cls.parent_program = self.program
                cls.status = ClassStatus.DRAFT
        else:  # edit actions
            try:
                cls = ClassSubject.objects.get(id=int(clsid))
            except (TypeError, ClassSubject.DoesNotExist):
                raise ESPError(f"The class you're trying to edit (ID {repr(clsid)}) does not exist!", log=False)
        
        # Get custom fields to handle them separately
        custom_fields = get_custom_fields()
        custom_data = {}
        
        # Handle ALL fields systematically, following the same pattern as set_class_data
        for field_name, field_value in reg_data.items():
            # Skip special Django form fields and section-specific fields
            if field_name in ['csrfmiddlewaretoken', 'class_reg_page', 'save_action', 'manage', 'manage_submit', 'class_id']:
                continue
                
            # Handle section-specific fields (skip for now, handled separately)
            if field_name.startswith('section_'):
                continue
                
            # Handle resource request fields (skip for now, handled separately)
            if field_name.startswith('request-'):
                continue
                
            # Handle custom fields separately
            if field_name in custom_fields:
                custom_data[field_name] = field_value
                continue
                
            # Handle special fields that need specific processing
            if field_name == 'category':
                if field_value:
                    try:
                        cls.category = ClassCategories.objects.get(id=int(field_value))
                    except (ClassCategories.DoesNotExist, ValueError):
                        pass  # Skip invalid category for drafts
                continue
                
            if field_name == 'duration':
                if field_value:
                    try:
                        cls.duration = Decimal(str(field_value))
                    except (ValueError, TypeError):
                        cls.duration = None
                continue
                
            if field_name == 'allow_lateness':
                cls.allow_lateness = field_value == 'on'
                continue
                
            if field_name == 'optimal_class_size_range':
                if field_value:
                    try:
                        cls.optimal_class_size_range = ClassSizeRange.objects.get(id=int(field_value))
                    except (ClassSizeRange.DoesNotExist, ValueError):
                        cls.optimal_class_size_range = None
                continue
                
            if field_name == 'allowable_class_size_ranges':
                if field_value:
                    try:
                        # Handle both single value and lists
                        if isinstance(field_value, list):
                            range_ids = field_value
                        else:
                            range_ids = reg_data.getlist('allowable_class_size_ranges')
                        if range_ids:
                            cls.allowable_class_size_ranges.set(ClassSizeRange.objects.filter(id__in=range_ids))
                    except (ClassSizeRange.DoesNotExist, ValueError):
                        pass
                continue
            
            # Handle numeric fields with type conversion
            numeric_fields = ['grade_min', 'grade_max', 'class_size_min', 'class_size_max', 'class_size_optimal', 'session_count']
            if field_name in numeric_fields:
                if field_value:
                    try:
                        setattr(cls, field_name, int(field_value))
                    except (ValueError, TypeError):
                        # Set reasonable defaults for drafts
                        if field_name == 'session_count':
                            cls.session_count = 1
                        elif field_name in ['grade_min']:
                            setattr(cls, field_name, 0)
                        elif field_name in ['grade_max']:
                            setattr(cls, field_name, 12)
                        else:
                            setattr(cls, field_name, None)
                else:
                    # For drafts, allow empty numeric fields (set to None instead of default)
                    if field_name not in ['grade_min', 'grade_max']:  # Keep grade defaults
                        setattr(cls, field_name, None)
                continue
            
            # Handle all other text/char fields directly - ALLOW EMPTY VALUES FOR DRAFTS
            text_fields = ['title', 'class_info', 'message_for_directors', 'prereqs', 'schedule', 
                          'requested_room', 'requested_special_resources', 'directors_notes', 
                          'purchase_requests', 'class_style', 'hardness_rating']
            
            if field_name in text_fields:
                # For drafts, allow empty values - this is the key change
                setattr(cls, field_name, field_value or '')
                continue
            
            # Handle any other fields that might be in the model but not explicitly listed
            if hasattr(cls, field_name) and field_name not in ['id', 'parent_program', 'status', 'timestamp']:
                # Try to set the field directly if it exists
                try:
                    setattr(cls, field_name, field_value)
                except (ValueError, TypeError):
                    # If type conversion fails, skip it for drafts
                    pass
        
        # Save custom form data
        cls.custom_form_data = custom_data
        
        # Save the class first
        cls.save()
        
        # Associate teacher for new drafts
        if action in ['create', 'createopenclass']:
            if not cls.teachers.filter(id=user.id).exists():
                cls.teachers.add(user)
        
        # Handle sections - get num_sections safely
        num_sections = 1
        if 'num_sections' in reg_data:
            try:
                num_sections = int(reg_data['num_sections'])
            except (ValueError, TypeError):
                num_sections = 1
        
        # Update sections
        self.update_class_sections(cls, num_sections)
        
        # Handle meeting times if provided
        if 'meeting_times' in reg_data and reg_data['meeting_times']:
            try:
                # Handle both single ID and list of IDs
                if isinstance(reg_data['meeting_times'], list):
                    meeting_time_ids = reg_data['meeting_times']
                else:
                    meeting_time_ids = reg_data.getlist('meeting_times')
                if meeting_time_ids:
                    cls.meeting_times.set(Event.objects.filter(id__in=meeting_time_ids))
            except (Event.DoesNotExist, ValueError):
                pass
        
        # Handle resource requests (basic version for drafts)
        if 'request-TOTAL_FORMS' in reg_data:
            try:
                self._save_draft_resource_requests(cls, reg_data)
            except Exception:
                # If resource requests fail, don't break the draft save
                pass
        
        return cls
    
    def _save_draft_resource_requests(self, cls, reg_data):
        """Helper method to save resource requests for drafts without validation"""
        # Clear existing requests
        for section in cls.sections.all():
            section.clearResourceRequests()
        
        # Get total forms and create requests for each
        total_forms = int(reg_data.get('request-TOTAL_FORMS', '0'))
        
        for i in range(total_forms):
            resource_type_id = reg_data.get(f'request-{i}-resource_type')
            desired_value = reg_data.get(f'request-{i}-desired_value')
            
            if resource_type_id and desired_value:
                try:
                    resource_type = ResourceType.objects.get(id=int(resource_type_id))
                    for section in cls.sections.all():
                        rr = ResourceRequest()
                        rr.target = section
                        rr.res_type = resource_type
                        rr.desired_value = desired_value
                        rr.save()
                except (ResourceType.DoesNotExist, ValueError):
                    continue

    def get_forms(self, reg_data, form_class=TeacherClassRegForm):
        reg_form = form_class(self.crmi, reg_data)

        if 'request-TOTAL_FORMS' in reg_data:
            resource_formset = ResourceRequestFormSet(reg_data, prefix='request')
        else:
            resource_formset = None

        if not reg_form.is_valid() or (resource_formset and not
                                       resource_formset.is_valid()):
            raise ClassCreationValidationError(reg_form, resource_formset, "Invalid form data.  Please make sure you are using the official registration form, on esp.mit.edu.  If you are, please let us know how you got this error.")

        return reg_form, resource_formset

    def make_class_happen(self, cls, user, reg_form, resource_formset, editing=False):
        self.set_class_data(cls, reg_form)
        self.update_class_sections(cls, int(reg_form.cleaned_data['num_sections']))

        #   Associate current user with class if it is being created.
        if user and not editing:
            self.associate_teacher_with_class(cls, user)

        self.add_rsrc_requests_to_class(cls, resource_formset)

        #   If someone is editing the class who isn't teaching it, don't unapprove it.
        if user in cls.get_teachers():
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

        if 'allowable_class_size_ranges' in reg_form.cleaned_data and reg_form.cleaned_data['allowable_class_size_ranges']:
            cls.allowable_class_size_ranges = ClassSizeRange.objects.filter(id__in=reg_form.cleaned_data['allowable_class_size_ranges'])

        #   Set title of class explicitly
        cls.title = reg_form.cleaned_data['title']
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

    def associate_teacher_with_class(self, cls, user):
        self.add_teacher_to_program_mailinglist(user)
        cls.makeTeacher(user)

    def force_availability(self, user):
        if len(user.getAvailableTimes(self.program)) == 0:
            for ts in self.program.getTimeSlots():
                user.addAvailableTime(self.program, ts)
            note = 'Availability was set automatically by the server in order to clear space for a newly registered class.'
            self.send_availability_email(user, note)

    def send_availability_email(self, teacher, note=None):
        timeslots = teacher.getAvailableTimes(self.program, ignore_classes=True)
        email_title = f'Availability for {self.program.niceName()}: {teacher.name()}'
        email_from = f'{self.program.program_type} Registration System <server@{settings.EMAIL_HOST_SENDER}>'
        email_context = {'teacher': teacher,
                         'timeslots': timeslots,
                         'program': self.program,
                         'curtime': datetime.now(),
                         'note': note,
                         'DEFAULT_HOST': settings.DEFAULT_HOST}
        email_contents = render_to_string('program/modules/availabilitymodule/update_email.txt', email_context)
        email_to = [teacher.get_email_sendto_address()]
        send_mail(email_title, email_contents, email_from, email_to, False)

    def teacher_has_time(self, user, hours):
        return (user.getTaughtTime(self.program, include_scheduled=True) + timedelta(hours=hours) \
                <= self.program.total_duration())

    def require_teacher_has_time(self, user, current_user, hours):
        if not self.teacher_has_time(user, hours):
            if user == current_user:
                message = 'We love you too!  However, you attempted to register for more hours of class than we have in the program.  Please go back to the class editing page and reduce the duration, or remove or shorten other classes to make room for this one.'
            else:
                message = f"{user.name()} doesn't have enough free time to teach a class of this length.  Please go back to the class editing page and reduce the duration, or have {user.first_name} remove or shorten other classes to make room for this one."
            raise ESPError(message, log=False)

    def add_teacher_to_program_mailinglist(self, user):
        add_list_member(f"{self.program.program_type}_{self.program.program_instance}-teachers", user)

    def add_rsrc_requests_to_class(self, cls, resource_formset):
        for sec in cls.get_sections():
            sec.clearResourceRequests()
            if resource_formset:
                for resform in resource_formset.forms:
                    self.import_resource_formset(sec, resform)

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

    def generate_director_mail_context(self, cls):
        new_data = cls.__dict__
        mail_ctxt = dict(new_data.items())

        mail_ctxt['title'] = cls.title
        mail_ctxt['one'] = cls.parent_program.program_type
        mail_ctxt['two'] = cls.parent_program.program_instance
        mail_ctxt['DEFAULT_HOST'] = settings.DEFAULT_HOST

        # Make some of the fields in new_data nicer for viewing.
        mail_ctxt['category'] = ClassCategories.objects.get(id=new_data['category_id']).category
        mail_ctxt['global_resources'] = cls.get_sections()[0].getResourceRequests()

        # Optimal and allowable class size ranges.
        if new_data.get('optimal_class_size_range_id') is not None:
            opt_range = ClassSizeRange.objects.get(id=new_data['optimal_class_size_range_id'])
            mail_ctxt['optimal_class_size_range'] = str(opt_range.range_min) + "-" + str(opt_range.range_max)
        else:
            mail_ctxt['optimal_class_size_range'] = ''
        try:
            mail_ctxt['allowable_class_size_ranges'] = cls.allowable_class_size_ranges.all()
        except AttributeError:
            # If the allowable_class_size_ranges field doesn't exist, just don't do anything.
            pass

        mail_ctxt['teachers'] = []
        for teacher in cls.get_teachers():
            teacher_ctxt = {'teacher': teacher}
            # Provide information about whether or not teacher's from MIT.
            last_profile = teacher.getLastProfile()
            if last_profile.teacher_info is not None:
                teacher_ctxt['from_here'] = last_profile.teacher_info.from_here
                teacher_ctxt['college'] = last_profile.teacher_info.college
            else: # This teacher never filled out their teacher profile!
                teacher_ctxt['from_here'] = "[Teacher hasn't filled out teacher profile!]"
                teacher_ctxt['college'] = "[Teacher hasn't filled out teacher profile!]"

            # Get a list of the programs this person has taught for in the past, if any.
            teacher_ctxt['taught_programs'] = ', '.join([prog.niceName() for prog in teacher.getTaughtPrograms().order_by('pk').exclude(id=self.program.id)])
            mail_ctxt['teachers'].append(teacher_ctxt)
        return mail_ctxt


    def send_class_mail_to_directors(self, cls, create = True):
        mail_ctxt = self.generate_director_mail_context(cls)
        subject = "Comments for " + cls.emailcode() + ': ' + cls.title

        if not create:
            subject = "Re: " + subject

        # add program email tag
        subject = '['+self.program.niceName()+'] ' + subject

        recipients = [teacher.email for teacher in cls.get_teachers()]
        if recipients:
            send_mail(subject, \
                      render_to_string('program/modules/teacherclassregmodule/classreg_email', mail_ctxt), \
                      (ESPUser.email_sendto_address(self.program.director_email, f'{self.program.program_type} Class Registration')), \
                      recipients, False)

        if self.program.director_email:
            mail_ctxt['admin'] = True
            send_mail(subject, \
                      render_to_string('program/modules/teacherclassregmodule/classreg_email', mail_ctxt), \
                      (ESPUser.email_sendto_address(self.program.director_email, f'{self.program.program_type} Class Registration')), \
                      [self.program.getDirectorCCEmail()], False)
