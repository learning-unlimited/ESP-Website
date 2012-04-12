from django import forms
from esp.tagdict.models import Tag
from esp.utils.forms import SizedCharField, FormWithRequiredCss, FormUnrestrictedOtherUser, FormWithTagInitialValues, StrippedCharField
from esp.db.forms import AjaxForeignKeyNewformField
from esp.utils.widgets import SplitDateWidget
from esp.users.models import K12School, StudentInfo
from esp.utils.defaultclass import defaultclass
from datetime import datetime
from esp.program.models import RegistrationProfile
from django.conf import settings
import re
import simplejson as json
from django.contrib.localflavor.us.forms import USPhoneNumberField

# SRC: esp/program/manipulators.py

_phone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
_localphone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
_states = ['AL' , 'AK' , 'AR', 'AZ' , 'CA' , 'CO' , 'CT' , 'DC' , 'DE' , 'FL' , 'GA' , 'GU' , 'HI' , 'IA' , 'ID'  ,'IL','IN'  ,'KS'  ,'KY'  ,'LA'  ,'MA' ,'MD'  ,'ME'  ,'MI'  ,'MN'  ,'MO' ,'MS'  ,'MT'  ,'NC'  ,'ND' ,'NE'  ,'NH'  ,'NJ'  ,'NM' ,'NV'  ,'NY' ,'OH'  , 'OK' ,'OR'  ,'PA'  ,'PR' ,'RI'  ,'SC'  ,'SD'  ,'TN' ,'TX'  ,'UT'  ,'VA'  ,'VI'  ,'VT'  ,'WA'  ,'WI'  ,'WV' ,'WY' ,'Canada', 'UK']


class PhoneNumberField(forms.CharField):
    """ Field for phone number. If area code not given, local_areacode is used instead. """
    def __init__(self, length=12, max_length=14, local_areacode = None, *args, **kwargs):
        forms.CharField.__init__(self, max_length=max_length, *args, **kwargs)
        self.widget.attrs['size'] = length
        if local_areacode:
            self.areacode = local_areacode
        else:
            self.areacode = None

    def clean(self, value):
        if value is None or value == '':
            return ''
        m = _phone_re.match(value)
        if m:
            numbers = m.groups()
            value = "".join(numbers[:3]) + '-' + "".join(numbers[3:6]) + '-' + "".join(numbers[6:])
            return value

        #   Check for a Tag containing the default area code.
        if self.areacode is None:
            tag_areacode = Tag.getTag('local_areacode')
            if tag_areacode:
                self.areacode = tag_areacode

        if self.areacode is not None:
            m = _localphone_re.match(value)
            if m:
                numbers = m.groups()
                value = self.areacode + '-' + "".join(numbers[:3]) + '-' + "".join(numbers[3:])
                return value
        raise forms.ValidationError('Phone numbers must be a valid US number. "%s" is invalid.' % value)

class DropdownOtherWidget(forms.MultiWidget):
    """
    A widget that presents a dropdown list of choices, as well as an 'Other...' textbox
    """
    def __init__(self, choices, use_textarea = False, attrs=None):
        widgets = (forms.Select(attrs=attrs, choices=choices),
                   forms.Textarea(attrs=attrs) if use_textarea else forms.TextInput(attrs=attrs))
        super(DropdownOtherWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if not value:
            return ['', '']
        retVal = value.split(':')
        if len(retVal) != 2:
            return ['','']
        return retVal

class DropdownOtherField(forms.MultiValueField):
    def compress(self, data_list):
        if data_list:
            return ':'.join(data_list)
        return ''

    def __init__(self, *args, **kwargs):
        super(DropdownOtherField, self).__init__(*args, **kwargs)
        self.fields = (forms.CharField(), forms.CharField(required=False),)

# TODO: Try to adapt some of these for ModelForm?
class UserContactForm(FormUnrestrictedOtherUser, FormWithTagInitialValues):
    """ Base for contact form """

    first_name = StrippedCharField(length=25, max_length=64)
    last_name = StrippedCharField(length=30, max_length=64)
    e_mail = forms.EmailField()
    phone_day = USPhoneNumberField(required=False)
    phone_cell = USPhoneNumberField(required=False)
    receive_txt_message = forms.BooleanField(required=False)
    address_street = StrippedCharField(length=40, max_length=100)
    address_city = StrippedCharField(length=20, max_length=50)
    address_state = forms.ChoiceField(choices=zip(_states,_states))
    address_zip = StrippedCharField(length=5, max_length=5)
    address_postal = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(UserContactForm, self).__init__(*args, **kwargs)
        if Tag.getTag('request_student_phonenum', default='True') == 'False':
            del self.fields['phone_day']
        if not Tag.getTag('text_messages_to_students'):
            del self.fields['receive_txt_message']

    def clean(self):
        super(UserContactForm, self).clean()
        if self.user.isTeacher() or Tag.getTag('request_student_phonenum', default='True') != 'False':
            if self.cleaned_data.get('phone_day','') == '' and self.cleaned_data.get('phone_cell','') == '':
                raise forms.ValidationError("Please provide either a day phone or cell phone number in your personal contact information.")
        if self.cleaned_data.get('receive_txt_message', None) and self.cleaned_data.get('phone_cell','') == '':
            raise forms.ValidationError("Please specify your cellphone number if you ask to receive text messages.")
        return self.cleaned_data

UserContactForm.base_fields['e_mail'].widget.attrs['size'] = 25

class EmergContactForm(FormUnrestrictedOtherUser):
    """ Contact form for emergency contacts """

    emerg_first_name = StrippedCharField(length=25, max_length=64)
    emerg_last_name = StrippedCharField(length=30, max_length=64)
    emerg_e_mail = forms.EmailField(required=False)
    emerg_phone_day = USPhoneNumberField()
    emerg_phone_cell = USPhoneNumberField(required=False)
    emerg_address_street = StrippedCharField(length=40, max_length=100)
    emerg_address_city = StrippedCharField(length=20, max_length=50)
    emerg_address_state = forms.ChoiceField(choices=zip(_states,_states))
    emerg_address_zip = StrippedCharField(length=5, max_length=5)
    emerg_address_postal = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean(self):
        super(EmergContactForm, self).clean()
        if self.cleaned_data.get('emerg_phone_day','') == '' and self.cleaned_data.get('emerg_phone_cell','') == '':
            raise forms.ValidationError("Please provide either a day phone or cell phone for your emergency contact.")
        return self.cleaned_data


class GuardContactForm(FormUnrestrictedOtherUser):
    """ Contact form for guardians """

    guard_first_name = StrippedCharField(length=25, max_length=64)
    guard_last_name = StrippedCharField(length=30, max_length=64)
    guard_no_e_mail = forms.BooleanField(required=False)
    guard_e_mail = forms.EmailField(required=False)
    guard_phone_day = USPhoneNumberField()
    guard_phone_cell = USPhoneNumberField(required=False)

    def __init__(self, *args, **kwargs):
        super(GuardContactForm, self).__init__(*args, **kwargs)
    
        if not Tag.getTag('allow_guardian_no_email'):
            if Tag.getTag('require_guardian_email'):
                self.fields['guard_e_mail'].required = True
            del self.fields['guard_no_e_mail']

    def clean_guard_e_mail(self):
        if 'guard_e_mail' not in self.cleaned_data or len(self.cleaned_data['guard_e_mail']) < 3:
            if Tag.getTag('require_guardian_email') and not self.cleaned_data['guard_no_e_mail']:
                if Tag.getTag('allow_guardian_no_email'):
                    raise forms.ValidationError("Please enter the e-mail address of your parent/guardian.  If they do not have access to e-mail, check the appropriate box.")
                else:
                    raise forms.ValidationError("Please enter the e-mail address of your parent/guardian.")
        else:
            return self.cleaned_data['guard_e_mail']

    def clean(self):
        super(GuardContactForm, self).clean()
        if self.cleaned_data.get('guard_phone_day','') == '' and self.cleaned_data.get('guard_phone_cell','') == '':
            raise forms.ValidationError("Please provide either a day phone or cell phone for your parent/guardian.")
        return self.cleaned_data

HeardAboutESPChoices = (
    'Other...',
    'Teacher or Counselor',
    'Splash representative visited my school',
    'Parents',
    'Friends',
    'Poster at school',
    'Poster in some other public place',
    'Facebook',
    'Newspaper or magazine',
    'Radio or TV',
    'I attended another program',
    'I came last year',
    )

WhatToDoAfterHS = (
    'Other...',
    "I don't know yet",
    'Get a job',
    'Go to community college',
    'Go to a 4-year college or university',
    'Go to a trade school',
    'Take the year off',
    )

HowToGetToProgram = (
    'Other...',
    'My school has already arranged for a bus',
    'I will ask my teachers and counselors to arrange for a bus for me and my peers',
    'My parent/guardian will drive me',
    'I will take mass transit (bus, train/subway, etc)',
    'I will drive myself',
    "I will get a ride with my friends' parents/guardians",
    'I will walk or ride my bike, skateboard, etc',
    )

class StudentInfoForm(FormUnrestrictedOtherUser):
    """ Extra student-specific information """
    from esp.users.models import ESPUser
    from esp.users.models import shirt_sizes, shirt_types, food_choices

    graduation_year = forms.ChoiceField(choices=[('', '')]+[(str(ESPUser.YOGFromGrade(x)), str(x)) for x in range(7,13)])
    k12school = AjaxForeignKeyNewformField(key_type=K12School, field_name='k12school', shadow_field_name='school', required=False, label='School')
    unmatched_school = forms.BooleanField(required=False)
    school = forms.CharField(max_length=128, required=False)
    dob = forms.DateField(widget=SplitDateWidget())
    studentrep = forms.BooleanField(required=False)
    studentrep_expl = forms.CharField(required=False)
    heard_about = DropdownOtherField(required=False, widget=DropdownOtherWidget(choices=zip(HeardAboutESPChoices, HeardAboutESPChoices)))#forms.CharField(required=False)
    shirt_size = forms.ChoiceField(choices=([('','')]+list(shirt_sizes)), required=False)
    shirt_type = forms.ChoiceField(choices=([('','')]+list(shirt_types)), required=False)
    food_preference = forms.ChoiceField(choices=([('','')]+list(food_choices)), required=False)

    medical_needs = forms.CharField(required=False)

    post_hs = DropdownOtherField(required=False, widget=DropdownOtherWidget(choices=zip(WhatToDoAfterHS, WhatToDoAfterHS)))
    transportation = DropdownOtherField(required=False, widget=DropdownOtherWidget(choices=zip(HowToGetToProgram, HowToGetToProgram)))
    schoolsystem_id = forms.CharField(max_length=32, required=False)
    schoolsystem_optout = forms.BooleanField(required=False)

    studentrep_error = True

    def __init__(self, user=None, *args, **kwargs):
        from esp.users.models import ESPUser
        super(StudentInfoForm, self).__init__(user, *args, **kwargs)

        self.allow_change_grade_level = Tag.getTag('allow_change_grade_level')

        ## All of these Tags may someday want to be made per-program somehow.
        ## We don't know the current program right now, though...
        show_studentrep_application = Tag.getTag('show_studentrep_application')
        if not show_studentrep_application:
            ## Only enable the Student Rep form optionally.
            del self.fields['studentrep']
        if (not show_studentrep_application) or show_studentrep_application == "no_expl":
            del self.fields['studentrep_expl']

        if not Tag.getTag('show_student_tshirt_size_options'):
            del self.fields['shirt_size']
            del self.fields['shirt_type']

        if not Tag.getTag('show_student_vegetarianism_options'):
            del self.fields['food_preference']

        #   Allow grade range of students to be customized by a Tag (default is 7-12)
        custom_grade_options = Tag.getTag('student_grade_options')
        if custom_grade_options:
            custom_grade_options = json.loads(custom_grade_options)
            self.fields['graduation_year'].choices = [('','')]+[(str(ESPUser.YOGFromGrade(x)), str(x)) for x in custom_grade_options]
            
        #   Add user's current grade if it is out of range and they have already filled out the profile.
        if user and user.registrationprofile_set.count() > 0:
            user_grade = user.getGrade()
            grade_tup = (str(ESPUser.YOGFromGrade(user_grade)), str(user_grade))
            if grade_tup not in self.fields['graduation_year'].choices:
                self.fields['graduation_year'].choices.insert(0, grade_tup)

        if Tag.getTag('show_student_graduation_years_not_grades'):            
            current_grad_year = self.ESPUser.current_schoolyear()
            new_choices = []
            for x in self.fields['graduation_year'].choices:
                if len(x[0]) > 0:
                    new_choices.append((str(x[0]), "%s (%sth grade)" % (x[0], x[1])))
                else:
                    new_choices.append(x)
            self.fields['graduation_year'].choices = new_choices

        if not Tag.getTag('ask_student_about_post_hs_plans'):
            del self.fields['post_hs']

        if not Tag.getTag('ask_student_about_transportation_to_program'):
            del self.fields['transportation']

        if not Tag.getTag('allow_change_grade_level'):
            if kwargs.has_key('initial'):
                initial_data = kwargs['initial']

                # Disable the age and grade fields if they already exist.
                if initial_data.has_key('graduation_year') and initial_data.has_key('dob'):
                    self.fields['graduation_year'].widget.attrs['disabled'] = "true"
                    self.fields['graduation_year'].required = False
                    self.fields['dob'].widget.attrs['disabled'] = "true"
                    self.fields['dob'].required = False
                    

        #   Add schoolsystem fields if directed by the Tag
        if Tag.getTag('schoolsystem'):
            sysinfo = json.loads(str(Tag.getTag('schoolsystem')))
            for key in ['label', 'required', 'help_text']:
                if key in sysinfo:
                    setattr(self.fields['schoolsystem_id'], key, sysinfo[key])
            if 'use_checkbox' in sysinfo and sysinfo['use_checkbox']:
                if 'label' in sysinfo:
                    self.fields['schoolsystem_optout'].help_text = '<span style="font-size: 0.8em;">Check this box if you don\'t have a %s</span>' % sysinfo['label']
                else:
                    self.fields['schoolsystem_optout'].help_text = '<span style="font-size: 0.8em;">Check this box if you don\'t have an ID number</span>'
            else:
                del self.fields['schoolsystem_optout']
        else:
            del self.fields['schoolsystem_id']
            del self.fields['schoolsystem_optout']

        #   Add field asking about medical needs if directed by the Tag
        if Tag.getTag('student_medical_needs'):
            self.fields['medical_needs'].widget = forms.Textarea(attrs={'cols': 40, 'rows': 3})
        else:
            del self.fields['medical_needs']
            
        #   Make the schoolsystem_id field non-required if schoolsystem_optout is checked
        if self.data and 'schoolsystem_optout' in self.data and 'schoolsystem_id' in self.data:
            self.data = self.data.copy()
            if self.data['schoolsystem_optout']:
                self.fields['schoolsystem_id'].required = False
                self.data['schoolsystem_id'] = ''
                
        #   The unmatched_school field is for students to opt out of selecting a K12School.
        #   If we don't require a K12School to be selected, don't bother showing that field.
        if not Tag.getTag('require_school_field', default=False):
            del self.fields['unmatched_school']
        
        self._user = user

    def repress_studentrep_expl_error(self):
        self.studentrep_error = False

    def clean_graduation_year(self):
        gy = self.cleaned_data['graduation_year'].strip()
        try:
            gy = str(abs(int(gy)))
        except:
            if gy != 'G':
                gy = 'N/A'
        return gy

    def clean_heard_about(self):
        if self.cleaned_data['heard_about'] == 'Other...:':
            raise forms.ValidationError("If 'Other...', please provide details")
        return self.cleaned_data['heard_about']

    def clean_post_hs(self):
        if self.cleaned_data['post_hs'] == 'Other...:':
            raise forms.ValidationError("If 'Other...', please provide details")
        return self.cleaned_data['post_hs']

    def clean_transportation(self):
        if self.cleaned_data['transportation'] == 'Other...:':
            raise forms.ValidationError("If 'Other...', please provide details")
        return self.cleaned_data['transportation']

    def clean_schoolsystem_id(self):
        if Tag.getTag('schoolsystem'):
            sysinfo = json.loads(str(Tag.getTag('schoolsystem')))
            if 'num_digits' in sysinfo:
                input_str = self.cleaned_data['schoolsystem_id'].strip()
                if len(input_str) > 0:
                    if len(input_str) != int(sysinfo['num_digits']) or not input_str.isdigit():
                        raise forms.ValidationError("Please enter a unique %d-digit number." % int(sysinfo['num_digits']))
            if 'check_unique' in sysinfo and sysinfo['check_unique']:
                if StudentInfo.objects.filter(schoolsystem_id=input_str).exclude(user=self._user).exists():
                    if len(input_str.strip('0')) != 0:
                        raise forms.ValidationError("Someone else has already entered CPS ID number '%s'." % input_str)
        return self.cleaned_data['schoolsystem_id']

    def clean(self):
        super(StudentInfoForm, self).clean()

        cleaned_data = self.cleaned_data

        show_studentrep_application = Tag.getTag('show_studentrep_application')
        if show_studentrep_application and show_studentrep_application != "no_expl":
            expl = self.cleaned_data['studentrep_expl'].strip()
            if self.studentrep_error and self.cleaned_data['studentrep'] and expl == '':
                raise forms.ValidationError("Please enter an explanation if you would like to become a student rep.")

        if not Tag.getTag('allow_change_grade_level'):
            user = self._user

            orig_prof = RegistrationProfile.getLastProfile(user)

            # If graduation year and dob were disabled, get old data.
            if (orig_prof.id is not None) and (orig_prof.student_info is not None):

                if not cleaned_data.has_key('graduation_year'):
                    # Get rid of the error saying this is missing
                    del self.errors['graduation_year']

                if not cleaned_data.has_key('dob'):
                    del self.errors['dob']

                # Always use the old birthdate if it exists, so that people can't
                # use something like Firebug to change their age/grade
                cleaned_data['graduation_year'] = orig_prof.student_info.graduation_year
                cleaned_data['dob'] = orig_prof.student_info.dob

        
        if Tag.getTag('require_school_field'):
            if not cleaned_data['k12school'] and not cleaned_data['unmatched_school']:
                raise forms.ValidationError("Please select your school from the dropdown list that appears as you type its name.  You will need to click on an entry to select it.  If you cannot find your school, please type in its full name and check the box below; we will do our best to add it to our database.")

        return cleaned_data
        
    
StudentInfoForm.base_fields['school'].widget.attrs['size'] = 24
StudentInfoForm.base_fields['studentrep_expl'].widget = forms.Textarea()
StudentInfoForm.base_fields['studentrep_expl'].widget.attrs['rows'] = 8
StudentInfoForm.base_fields['studentrep_expl'].widget.attrs['cols'] = 45


class TeacherInfoForm(FormWithRequiredCss):
    """ Extra teacher-specific information """

    from esp.users.models import shirt_sizes, shirt_types
    reimbursement_choices = [(False, 'I will pick up my reimbursement.'),
                             (True,  'Please mail me my reimbursement.')]
    from_here_answers = [ (True, "Yes"), (False, "No") ]

    graduation_year = SizedCharField(length=4, max_length=4, required=False)
    is_graduate_student = forms.BooleanField(required=False, label='Graduate student?')
    from_here = forms.ChoiceField(choices=from_here_answers, widget = forms.RadioSelect(), label='Are you currently enrolled at %s?' % settings.INSTITUTION_NAME)
    school = SizedCharField(length=24, max_length=128, required=False)
    major = SizedCharField(length=30, max_length=32, required=False)
    shirt_size = forms.ChoiceField(choices=([('','')]+list(shirt_sizes)), required=False)
    shirt_type = forms.ChoiceField(choices=([('','')]+list(shirt_types)), required=False)
    full_legal_name = SizedCharField(length=24, max_length=128, required=False)
    university_email = forms.EmailField(required=False)
    student_id = SizedCharField(length=24, max_length=128, required=False)
    mail_reimbursement = forms.ChoiceField(choices=reimbursement_choices, widget=forms.RadioSelect(), required=False)

    def __init__(self, *args, **kwargs):
        super(TeacherInfoForm, self).__init__(*args, **kwargs)
        if not Tag.getTag('teacherinfo_reimbursement_options', default=False):
            reimbursement_fields = ['full_legal_name', 'university_email', 'student_id', 'mail_reimbursement']
            for field_name in reimbursement_fields:
                del self.fields[field_name]

        if Tag.getTag('teacherinfo_shirt_options') == 'False':
            del self.fields['shirt_size']
            del self.fields['shirt_type']
        elif Tag.getTag('teacherinfo_shirt_type_selection') == 'False':
            del self.fields['shirt_type']
            
        if Tag.getTag('teacherinfo_shirt_size_required'):
            self.fields['shirt_size'].required = True
            self.fields['shirt_size'].widget.attrs['class'] = 'required'
        if Tag.getTag('teacherinfo_reimbursement_checks') == 'False':
            del self.fields['mail_reimbursement']
            
    def clean(self):
        super(TeacherInfoForm, self).clean()
        cleaned_data = self.cleaned_data

        # If teacher is not from MIT, make sure they've filled in the next box
        from_here = cleaned_data.get('from_here')
        school = cleaned_data.get('school')

        if from_here == "False" and school == "":
            msg = u'Please enter your affiliation if you are not from %s.' % settings.INSTITUTION_NAME
            self._errors['school'] = forms.util.ErrorList([msg])
            del cleaned_data['from_here']
            del cleaned_data['school']

        return cleaned_data

TeacherInfoForm.base_fields['graduation_year'].widget.attrs['size'] = 4
TeacherInfoForm.base_fields['graduation_year'].widget.attrs['maxlength'] = 4

class EducatorInfoForm(FormWithRequiredCss):
    """ Extra educator-specific information """

    subject_taught = SizedCharField(length=12, max_length=64, required=False)
    grades_taught = SizedCharField(length=10, max_length=16, required=False)
    school = SizedCharField(length=24, max_length=128, required=False)
    position = SizedCharField(length=10, max_length=32, required=False)

class GuardianInfoForm(FormWithRequiredCss):
    """ Extra guardian-specific information """

    year_finished = forms.IntegerField(min_value=1, required=False)
    num_kids = forms.IntegerField(min_value=1, required=False)

GuardianInfoForm.base_fields['year_finished'].widget.attrs['size'] = 4
GuardianInfoForm.base_fields['year_finished'].widget.attrs['maxlength'] = 4
GuardianInfoForm.base_fields['num_kids'].widget.attrs['size'] = 3
GuardianInfoForm.base_fields['num_kids'].widget.attrs['maxlength'] = 16

class StudentProfileForm(UserContactForm, EmergContactForm, GuardContactForm, StudentInfoForm):
    """ Form for student profiles """
StudentProfileForm = defaultclass(StudentProfileForm)

class TeacherProfileForm(UserContactForm, TeacherInfoForm):
    """ Form for teacher profiles """
    def __init__(self, *args, **kwargs):
        super(TeacherProfileForm, self).__init__(*args, **kwargs)
        for field_name in Tag.getTag('teacher_profile_hide_fields', default='').split(','):
            if field_name in self.fields:
                del self.fields[field_name]

class GuardianProfileForm(UserContactForm, GuardianInfoForm):
    """ Form for guardian profiles """

class EducatorProfileForm(UserContactForm, EducatorInfoForm):
    """ Form for educator profiles """

class VolunteerProfileForm(UserContactForm):
    pass

class VisitingUserInfo(FormUnrestrictedOtherUser):
    profession = SizedCharField(length=12, max_length=64, required=False)

class MinimalUserInfo(FormUnrestrictedOtherUser):
    first_name = StrippedCharField(length=25, max_length=64)
    last_name = StrippedCharField(length=30, max_length=64)
    e_mail = forms.EmailField()
    address_street = StrippedCharField(length=40, max_length=100)
    address_city = StrippedCharField(length=20, max_length=50)
    address_state = forms.ChoiceField(choices=zip(_states,_states))
    address_zip = StrippedCharField(length=5, max_length=5)
    address_postal = forms.CharField(required=False, widget=forms.HiddenInput())

_grad_years = range(datetime.now().year, datetime.now().year + 6)

class UofCProfileForm(MinimalUserInfo, FormWithTagInitialValues):
    graduation_year = forms.ChoiceField(choices=zip(_grad_years, _grad_years))
    major = SizedCharField(length=30, max_length=32, required=False)

    def clean_graduation_year(self):
        gy = self.cleaned_data['graduation_year'].strip()
        try:
            gy = str(abs(int(gy)))
        except:
            if gy != 'G':
                gy = 'N/A'
        return gy
    
class AlumProfileForm(MinimalUserInfo, FormWithTagInitialValues):
    """ This is the visiting-teacher contact form as used by UChicago's Ripple program """
    graduation_year = SizedCharField(length=4, max_length=4, required=False)
    major = SizedCharField(length=30, max_length=32, required=False)

    def clean_graduation_year(self):
        gy = self.cleaned_data['graduation_year'].strip()
        try:
            gy = str(abs(int(gy)))
        except:
            if gy != 'G':
                gy = 'N/A'
        return gy

class UofCProfForm(MinimalUserInfo, FormWithTagInitialValues):
    major = SizedCharField(length=30, max_length=32, label="Department", required=False)

class VisitingGenericUserProfileForm(MinimalUserInfo, FormWithTagInitialValues):
    """ This is a form for a generic visitor user """
    major = SizedCharField(length=30, max_length=32, label="Profession", required=False)
