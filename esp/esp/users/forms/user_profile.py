from django import forms
from esp.tagdict.models import Tag
from esp.utils.forms import SizedCharField, FormWithRequiredCss, FormUnrestrictedOtherUser, FormWithTagInitialValues
from esp.db.forms import AjaxForeignKeyNewformField
from esp.utils.widgets import SplitDateWidget
from esp.users.models import K12School, StudentInfo
from esp.utils.defaultclass import defaultclass
from datetime import datetime
from esp.program.models import RegistrationProfile
import re

# SRC: esp/program/manipulators.py

_phone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
_localphone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
_states = ['AL' , 'AK' , 'AR', 'AZ' , 'CA' , 'CO' , 'CT' , 'DC' , 'DE' , 'FL' , 'GA' , 'GU' , 'HI' , 'IA' , 'ID'  ,'IL','IN'  ,'KS'  ,'KY'  ,'LA'  ,'MA' ,'MD'  ,'ME'  ,'MI'  ,'MN'  ,'MO' ,'MS'  ,'MT'  ,'NC'  ,'ND' ,'NE'  ,'NH'  ,'NJ'  ,'NM' ,'NV'  ,'NY' ,'OH'  , 'OK' ,'OR'  ,'PA'  ,'PR' ,'RI'  ,'SC'  ,'SD'  ,'TN' ,'TX'  ,'UT'  ,'VA'  ,'VI'  ,'VT'  ,'WA'  ,'WI'  ,'WV' ,'WY' ,'Canada']


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

    first_name = SizedCharField(length=25, max_length=64)
    last_name = SizedCharField(length=30, max_length=64)
    e_mail = forms.EmailField()
    phone_day = PhoneNumberField(required=False)
    phone_cell = PhoneNumberField(required=False)
    receive_txt_message = forms.BooleanField(required=False)
    address_street = SizedCharField(length=40, max_length=100)
    address_city = SizedCharField(length=20, max_length=50)
    address_state = forms.ChoiceField(choices=zip(_states,_states))
    address_zip = SizedCharField(length=5, max_length=5)
    address_postal = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(UserContactForm, self).__init__(*args, **kwargs)
        if not Tag.getTag('text_messages_to_students'):
            del self.fields['receive_txt_message']

    def clean_phone_cell(self):
        if self.cleaned_data.get('phone_day','') == '' and self.cleaned_data.get('phone_cell','') == '':
            raise forms.ValidationError("Please provide either a day phone or cell phone.")
        if self.cleaned_data.get('receive_txt_message', '') == '' and self.cleaned_data.get('phone_cell','') == '':
            raise forms.ValidationError("Please specify your cellphone number if you ask to receive text messages")
        return self.cleaned_data['phone_cell']
UserContactForm.base_fields['e_mail'].widget.attrs['size'] = 25

class TeacherContactForm(UserContactForm):
    """ Contact form for teachers """

    # Require both phone numbers for teachers.
    phone_day = PhoneNumberField()
    phone_cell = PhoneNumberField()
    
class EmergContactForm(FormUnrestrictedOtherUser):
    """ Contact form for emergency contacts """

    emerg_first_name = SizedCharField(length=25, max_length=64)
    emerg_last_name = SizedCharField(length=30, max_length=64)
    emerg_e_mail = forms.EmailField(required=False)
    emerg_phone_day = PhoneNumberField()
    emerg_phone_cell = PhoneNumberField(required=False)
    emerg_address_street = SizedCharField(length=40, max_length=100)
    emerg_address_city = SizedCharField(length=20, max_length=50)
    emerg_address_state = forms.ChoiceField(choices=zip(_states,_states))
    emerg_address_zip = SizedCharField(length=5, max_length=5)
    emerg_address_postal = forms.CharField(required=False, widget=forms.HiddenInput())


class GuardContactForm(FormUnrestrictedOtherUser):
    """ Contact form for guardians """

    guard_first_name = SizedCharField(length=25, max_length=64)
    guard_last_name = SizedCharField(length=30, max_length=64)
    guard_e_mail = forms.EmailField(required=False)
    guard_phone_day = PhoneNumberField()
    guard_phone_cell = PhoneNumberField(required=False)

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

    graduation_year = forms.ChoiceField(choices=[(str(ESPUser.YOGFromGrade(x)), str(x)) for x in range(7,13)])
    k12school = AjaxForeignKeyNewformField(key_type=K12School, field_name='k12school', shadow_field_name='school', required=False, label='School')
    school = forms.CharField(max_length=128, required=False)
    dob = forms.DateField(widget=SplitDateWidget())
    studentrep = forms.BooleanField(required=False)
    studentrep_expl = forms.CharField(required=False)
    heard_about = DropdownOtherField(required=False, widget=DropdownOtherWidget(choices=zip(HeardAboutESPChoices, HeardAboutESPChoices)))#forms.CharField(required=False)
    shirt_size = forms.ChoiceField(choices=([('','')]+list(shirt_sizes)), required=False)
    shirt_type = forms.ChoiceField(choices=([('','')]+list(shirt_types)), required=False)
    food_preference = forms.ChoiceField(choices=([('','')]+list(food_choices)), required=False)

    post_hs = DropdownOtherField(required=False, widget=DropdownOtherWidget(choices=zip(WhatToDoAfterHS, WhatToDoAfterHS)))
    transportation = DropdownOtherField(required=False, widget=DropdownOtherWidget(choices=zip(HowToGetToProgram, HowToGetToProgram)))

    studentrep_error = True

    def __init__(self, user=None, *args, **kwargs):
        super(StudentInfoForm, self).__init__(user, *args, **kwargs)

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

        if not Tag.getTag('show_student_graduation_years_not_grades', default=True):            
            current_grad_year = self.ESPUser.current_schoolyear()
            self.fields['graduation_year'].widget.choices = [(str(12 - (x - current_grad_year)), "%d (%dth grade)" % (x, 12 - (x - current_grad_year))) for x in xrange(current_grad_year, current_grad_year + 6)]

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
                    self.fields['dob'].widget.attrs['disabled'] = "true"

        self._user = user


    def repress_studentrep_expl_error(self):
        self.studentrep_error = False

    def clean_studentrep_expl(self):
        expl = self.cleaned_data['studentrep_expl'].strip()
        if self.studentrep_error and self.cleaned_data['studentrep'] and expl == '':
            raise forms.ValidationError("Please enter an explanation above.")
        return expl

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

    def clean(self):
        cleaned_data = self.cleaned_data

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
    from_here = forms.ChoiceField(choices=from_here_answers, widget = forms.RadioSelect(), label='Are you currently enrolled at the university running this program?')
    school = SizedCharField(length=24, max_length=128, required=False)
    major = SizedCharField(length=30, max_length=32, required=False)
    shirt_size = forms.ChoiceField(choices=([('','')]+list(shirt_sizes)), required=False)
    shirt_type = forms.ChoiceField(choices=([('','')]+list(shirt_types)), required=False)
    full_legal_name = SizedCharField(length=24, max_length=128, required=False)
    university_email = forms.EmailField(required=False)
    student_id = SizedCharField(length=24, max_length=128, required=False)
    mail_reimbursement = forms.ChoiceField(choices=reimbursement_choices, widget=forms.RadioSelect(), required=False)

    def clean(self):
        cleaned_data = self.cleaned_data

        # If teacher is not from MIT, make sure they've filled in the next box
        from_here = cleaned_data.get('from_here')
        school = cleaned_data.get('school')

        if from_here == "False" and school == "":
            msg = u'Please enter your affiliation if you are not from MIT.'
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

class TeacherProfileForm(TeacherContactForm, TeacherInfoForm):
    """ Form for teacher profiles """

class GuardianProfileForm(UserContactForm, GuardianInfoForm):
    """ Form for guardian profiles """

class EducatorProfileForm(UserContactForm, EducatorInfoForm):
    """ Form for educator profiles """

class VisitingUserInfo(FormUnrestrictedOtherUser):
    profession = SizedCharField(length=12, max_length=64, required=False)

class MinimalUserInfo(FormUnrestrictedOtherUser):
    first_name = SizedCharField(length=25, max_length=64)
    last_name = SizedCharField(length=30, max_length=64)
    e_mail = forms.EmailField()
    address_street = SizedCharField(length=40, max_length=100)
    address_city = SizedCharField(length=20, max_length=50)
    address_state = forms.ChoiceField(choices=zip(_states,_states))
    address_zip = SizedCharField(length=5, max_length=5)
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
    
class AlumProfileForm(MinimalUserInfo):
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

class UofCProfForm(MinimalUserInfo):
    major = SizedCharField(length=30, max_length=32, label="Department", required=False)

class VisitingGenericUserProfileForm(MinimalUserInfo):
    """ This is a form for a generic visitor user """
    major = SizedCharField(length=30, max_length=32, label="Profession", required=False)
