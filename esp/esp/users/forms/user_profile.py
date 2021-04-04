from django import forms
from esp.users.forms import _states
from esp.tagdict.models import Tag
from esp.utils.forms import SizedCharField, FormWithRequiredCss, FormUnrestrictedOtherUser, FormWithTagInitialValues, StrippedCharField
from esp.db.forms import AjaxForeignKeyNewformField
from esp.utils.widgets import SplitDateWidget
from esp.users.models import K12School, StudentInfo, AFFILIATION_UNDERGRAD, AFFILIATION_GRAD, AFFILIATION_POSTDOC, AFFILIATION_OTHER, AFFILIATION_NONE
from datetime import datetime
from esp.program.models import RegistrationProfile
from django.conf import settings
import json
from pytz import country_names
from localflavor.us.forms import USPhoneNumberField

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
    receive_txt_message = forms.TypedChoiceField(coerce=lambda x: x =='True', choices=((True, 'Yes'),(False, 'No')), widget=forms.RadioSelect)
    address_street = StrippedCharField(required=True, length=40, max_length=100)
    address_city = StrippedCharField(required=True, length=20, max_length=50)
    address_state = forms.ChoiceField(required=True, choices=zip(_states,_states), widget=forms.Select(attrs={'class': 'input-mini'}))
    address_zip = StrippedCharField(required=True, length=5, max_length=5, widget=forms.TextInput(attrs={'class': 'input-small'}))
    address_country = forms.ChoiceField(required=False, choices=[('', '(select a country)')] + sorted(country_names.items(), key = lambda x: x[1]), widget=forms.Select(attrs={'class': 'input-medium hidden'}))
    address_postal = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(UserContactForm, self).__init__(*args, **kwargs)
        if not Tag.getBooleanTag('request_student_phonenum'):
            del self.fields['phone_day']
        if not Tag.getBooleanTag('text_messages_to_students') or not self.user.isStudent():
            del self.fields['receive_txt_message']
        if self.user.isTeacher() and not Tag.getBooleanTag('teacher_address_required'):
            self.fields['address_street'].required = False
            if 'class' in self.fields['address_street'].widget.attrs and self.fields['address_street'].widget.attrs['class']:
                self.fields['address_street'].widget.attrs['class'] = self.fields['address_street'].widget.attrs['class'].replace('required', '')
            self.fields['address_city'].required = False
            if 'class' in self.fields['address_city'].widget.attrs and self.fields['address_city'].widget.attrs['class']:
                self.fields['address_city'].widget.attrs['class'] = self.fields['address_city'].widget.attrs['class'].replace('required', '')
            self.fields['address_state'].required = False
            if 'class' in self.fields['address_state'].widget.attrs and self.fields['address_state'].widget.attrs['class']:
                self.fields['address_state'].widget.attrs['class'] = self.fields['address_state'].widget.attrs['class'].replace('required', '')
            self.fields['address_zip'].required = False
            if 'class' in self.fields['address_zip'].widget.attrs and self.fields['address_zip'].widget.attrs['class']:
                self.fields['address_zip'].widget.attrs['class'] = self.fields['address_zip'].widget.attrs['class'].replace('required', '')

    def clean(self):
        super(UserContactForm, self).clean()
        if self.user.isTeacher() or (self.user.isStudent() and Tag.getBooleanTag('require_student_phonenum')):
            if 'phone_day' in self.fields or 'phone_cell' in self.fields:
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
    emerg_address_state = forms.ChoiceField(choices=zip(_states,_states), widget=forms.Select(attrs={'class': 'input-mini'}))
    emerg_address_zip = StrippedCharField(length=5, max_length=5, widget=forms.TextInput(attrs={'class': 'input-small'}))
    emerg_address_country = forms.ChoiceField(required=False, choices=[('', '(select a country)')] + sorted(country_names.items(), key = lambda x: x[1]), widget=forms.Select(attrs={'class': 'input-medium hidden'}))
    emerg_address_postal = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean(self):
        super(EmergContactForm, self).clean()
        if 'emerg_phone_day' in self.fields or 'emerg_phone_cell' in self.fields:
            if self.cleaned_data.get('emerg_phone_day','') == '' and self.cleaned_data.get('emerg_phone_cell','') == '':
                raise forms.ValidationError("Please provide either a day phone or cell phone for your emergency contact.")
        return self.cleaned_data


class GuardContactForm(FormUnrestrictedOtherUser):
    """ Contact form for guardians """

    guard_first_name = StrippedCharField(length=25, max_length=64)
    guard_last_name = StrippedCharField(length=30, max_length=64)
    guard_e_mail = forms.EmailField(required=False)
    guard_phone_day = USPhoneNumberField()
    guard_phone_cell = USPhoneNumberField(required=False)

    def clean(self):
        super(GuardContactForm, self).clean()
        if 'guard_phone_day' in self.fields or 'guard_phone_cell' in self.fields:
            if self.cleaned_data.get('guard_phone_day','') == '' and self.cleaned_data.get('guard_phone_cell','') == '':
                raise forms.ValidationError("Please provide either a day phone or cell phone for your parent/guardian.")
        return self.cleaned_data

HEARD_ABOUT_ESP_CHOICES = (
    '',
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

WHAT_TO_DO_AFTER_HS = (
    '',
    'Other...',
    "I don't know yet",
    'Get a job',
    'Go to community college',
    'Go to a 4-year college or university',
    'Go to a trade school',
    'Take the year off',
    )

HOW_TO_GET_TO_PROGRAM = (
    '',
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

    gender = forms.ChoiceField(choices=[('', ''), ('M', 'Male'), ('F', 'Female')], required=False)
    graduation_year = forms.ChoiceField(choices=[('', '')]+[(str(ESPUser.YOGFromGrade(x)), str(x)) for x in range(7,13)])
    k12school = AjaxForeignKeyNewformField(key_type=K12School, field_name='k12school', shadow_field_name='school', required=False, label='School')
    unmatched_school = forms.BooleanField(required=False)
    school = forms.CharField(max_length=128, required=False)
    dob = forms.DateField(widget=SplitDateWidget(min_year=datetime.now().year-20))
    studentrep = forms.BooleanField(required=False)
    studentrep_expl = forms.CharField(required=False)
    heard_about = DropdownOtherField(required=False, widget=DropdownOtherWidget(choices=zip(HEARD_ABOUT_ESP_CHOICES, HEARD_ABOUT_ESP_CHOICES)))#forms.CharField(required=False)
    shirt_size = forms.ChoiceField(choices=[], required=False)
    shirt_type = forms.ChoiceField(choices=[], required=False)
    food_preference = forms.ChoiceField(choices=[], required=False)

    medical_needs = forms.CharField(required=False)

    transportation = DropdownOtherField(required=False, widget=DropdownOtherWidget(choices=zip(HOW_TO_GET_TO_PROGRAM, HOW_TO_GET_TO_PROGRAM)))

    studentrep_error = True

    def __init__(self, user=None, *args, **kwargs):
        from esp.users.models import ESPUser
        super(StudentInfoForm, self).__init__(user, *args, **kwargs)

        self.fields['shirt_size'].choices = [('','')]+[(x.strip(), x.strip()) for x in Tag.getTag('student_shirt_sizes').split(',')]
        self.fields['shirt_type'].choices = [('','')]+[(x.strip(), x.strip()) for x in Tag.getTag('shirt_types').split(',')]
        self.fields['food_preference'].choices = [('','')]+[(x.strip(), x.strip()) for x in Tag.getTag('food_choices').split(',')]

        self.allow_change_grade_level = Tag.getBooleanTag('allow_change_grade_level')

        ## All of these Tags may someday want to be made per-program somehow.
        ## We don't know the current program right now, though...
        show_studentrep_application = Tag.getTag('show_studentrep_application')
        if not show_studentrep_application:
            ## Only enable the Student Rep form optionally.
            del self.fields['studentrep']
        if (not show_studentrep_application) or show_studentrep_application == "no_expl":
            del self.fields['studentrep_expl']

        if not Tag.getBooleanTag('show_student_tshirt_size_options'):
            del self.fields['shirt_size']
        if not Tag.getBooleanTag('studentinfo_shirt_type_selection'):
            del self.fields['shirt_type']

        if not Tag.getBooleanTag('show_student_vegetarianism_options'):
            del self.fields['food_preference']

        #   Allow grade range of students to be customized by a Tag (default is 7-12)
        self.fields['graduation_year'].choices = [('','')]+[(str(ESPUser.YOGFromGrade(x)), str(x)) for x in ESPUser.grade_options()]

        #   Add user's current grade if it is out of range and they have already filled out the profile.
        if user and user.registrationprofile_set.count() > 0:
            user_grade = user.getGrade()
            grade_tup = (str(ESPUser.YOGFromGrade(user_grade)), str(user_grade))
            # Prevent 0th grade from showing up -ageng 2013-08-26
            if grade_tup not in self.fields['graduation_year'].choices and user_grade > 0:
                self.fields['graduation_year'].choices.insert(0, grade_tup)

        #   Honor several possible Tags for customizing the fields that are displayed.
        if Tag.getBooleanTag('show_student_graduation_years_not_grades'):
            current_grad_year = self.ESPUser.current_schoolyear()
            new_choices = []
            for x in self.fields['graduation_year'].choices:
                if len(x[0]) > 0:
                    new_choices.append((str(x[0]), "%s (%sth grade)" % (x[0], x[1])))
                else:
                    new_choices.append(x)
            self.fields['graduation_year'].choices = new_choices

        if not Tag.getBooleanTag('student_profile_gender_field'):
            del self.fields['gender']

        if not Tag.getBooleanTag('ask_student_about_transportation_to_program'):
            del self.fields['transportation']

        if not Tag.getBooleanTag('allow_change_grade_level'):
            if 'initial' in kwargs:
                initial_data = kwargs['initial']

                # Disable the age and grade fields if they already exist.
                if 'graduation_year' in initial_data and 'dob' in initial_data:
                    self.fields['graduation_year'].widget.attrs['disabled'] = "true"
                    self.fields['graduation_year'].required = False
                    self.fields['dob'].widget.attrs['disabled'] = "true"
                    self.fields['dob'].required = False

        #   Add field asking about medical needs if directed by the Tag
        if Tag.getBooleanTag('student_medical_needs'):
            self.fields['medical_needs'].widget = forms.Textarea(attrs={'cols': 40, 'rows': 3})
        else:
            del self.fields['medical_needs']

        #   The unmatched_school field is for students to opt out of selecting a K12School.
        #   If we don't require a K12School to be selected, don't bother showing that field.
        if not Tag.getBooleanTag('require_school_field'):
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

    def clean_transportation(self):
        if self.cleaned_data['transportation'] == 'Other...:':
            raise forms.ValidationError("If 'Other...', please provide details")
        return self.cleaned_data['transportation']

    def clean(self):
        super(StudentInfoForm, self).clean()

        cleaned_data = self.cleaned_data

        show_studentrep_application = Tag.getTag('show_studentrep_application')
        if show_studentrep_application and show_studentrep_application != "no_expl":
            expl = self.cleaned_data['studentrep_expl'].strip()
            if self.studentrep_error and self.cleaned_data['studentrep'] and expl == '':
                raise forms.ValidationError("Please enter an explanation if you would like to become a student rep.")

        if not Tag.getBooleanTag('allow_change_grade_level'):
            user = self._user

            orig_prof = RegistrationProfile.getLastProfile(user)

            # If graduation year and dob were disabled, get old data.
            if (orig_prof.id is not None) and (orig_prof.student_info is not None):

                if not 'graduation_year' in cleaned_data:
                    # Get rid of the error saying this is missing
                    del self.errors['graduation_year']

                if not 'dob' in cleaned_data:
                    del self.errors['dob']

                # Always use the old birthdate if it exists, so that people can't
                # use something like Firebug to change their age/grade
                cleaned_data['graduation_year'] = orig_prof.student_info.graduation_year
                cleaned_data['dob'] = orig_prof.student_info.dob


        if Tag.getBooleanTag('require_school_field') and 'k12school' in self.fields:
            if not cleaned_data['k12school'] and not cleaned_data['unmatched_school']:
                raise forms.ValidationError("Please select your school from the dropdown list that appears as you type its name.  You will need to click on an entry to select it.  If you cannot find your school, please type in its full name and check the box below; we will do our best to add it to our database.")

        return cleaned_data


StudentInfoForm.base_fields['school'].widget.attrs['size'] = 24
StudentInfoForm.base_fields['studentrep_expl'].widget = forms.Textarea()
StudentInfoForm.base_fields['studentrep_expl'].widget.attrs['rows'] = 8
StudentInfoForm.base_fields['studentrep_expl'].widget.attrs['cols'] = 45

AFFILIATION_CHOICES = (
    (AFFILIATION_UNDERGRAD, 'Undergraduate Student'),
    (AFFILIATION_GRAD, 'Graduate Student'),
    (AFFILIATION_POSTDOC, 'Postdoc'),
    (AFFILIATION_OTHER, 'Other (please specify your affiliation)'),
    (AFFILIATION_NONE, 'No affiliation (please specify your school or employer)')
)

class TeacherInfoForm(FormWithRequiredCss):
    """ Extra teacher-specific information """

    reimbursement_choices = [(False, 'I will pick up my reimbursement.'),
                             (True,  'Please mail me my reimbursement.')]
    from_here_answers = [ (True, "Yes"), (False, "No") ]

    graduation_year = SizedCharField(length=4, max_length=4, required=False)
    affiliation = DropdownOtherField(required=False, widget=DropdownOtherWidget(choices=AFFILIATION_CHOICES), label ='What is your affiliation with %s?' % settings.INSTITUTION_NAME)
    major = SizedCharField(length=30, max_length=32, required=False)
    shirt_size = forms.ChoiceField(choices=[], required=False)
    shirt_type = forms.ChoiceField(choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super(TeacherInfoForm, self).__init__(*args, **kwargs)

        self.fields['shirt_size'].choices = [('','')]+[(x.strip(), x.strip()) for x in Tag.getTag('teacher_shirt_sizes').split(',')]
        self.fields['shirt_type'].choices = [('','')]+[(x.strip(), x.strip()) for x in Tag.getTag('shirt_types').split(',')]

        if not Tag.getBooleanTag('teacherinfo_shirt_options'):
            del self.fields['shirt_size']
            del self.fields['shirt_type']
        elif not Tag.getBooleanTag('teacherinfo_shirt_type_selection'):
            del self.fields['shirt_type']

    def clean(self):
        super(TeacherInfoForm, self).clean()
        cleaned_data = self.cleaned_data

        if 'affiliation' in self.fields:
            affiliation_field = self.fields['affiliation']
            affiliation, school = affiliation_field.widget.decompress(cleaned_data.get('affiliation'))
            if affiliation == '':
                msg = u'Please select your affiliation with %s.' % settings.INSTITUTION_NAME
                self.add_error('affiliation', msg)
            elif affiliation in (AFFILIATION_UNDERGRAD, AFFILIATION_GRAD, AFFILIATION_POSTDOC):
                cleaned_data['affiliation'] = affiliation_field.compress([affiliation, '']) # ignore the box
            else: # OTHER or NONE -- Make sure they entered something into the other box
                if school.strip() == '':
                    msg = u'Please select your affiliation with %s.' % settings.INSTITUTION_NAME
                    if affiliation == AFFILIATION_OTHER:
                        msg = u'Please enter your affiliation with %s.' % settings.INSTITUTION_NAME
                    elif affiliation == AFFILIATION_NONE:
                        msg = u'Please enter your school or employer.'
                    self.add_error('affiliation', msg)
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

# A list of fields (across all profile forms) that can not be deleted via profile_hide_fields tags
_undeletable_fields_all = ['e_mail']

# A list of student fields that can not be deleted via profile_hide_fields tags
_undeletable_fields_students = ['graduation_year']
class StudentProfileForm(UserContactForm, EmergContactForm, GuardContactForm, StudentInfoForm):
    """ Form for student profiles """
    def __init__(self, *args, **kwargs):
        super(StudentProfileForm, self).__init__(*args, **kwargs)
        for field_name in [x.strip().lower() for x in Tag.getTag('student_profile_hide_fields').split(',')]:
            if field_name in self.fields and field_name not in _undeletable_fields_all + _undeletable_fields_students:
                del self.fields[field_name]
            if field_name == 'phone_cell' and 'receive_txt_message' in self.fields:
                del self.fields['receive_txt_message']

# A list of teacher fields that can not be deleted via profile_hide_fields tags
_undeletable_fields_teachers = []
class TeacherProfileForm(UserContactForm, TeacherInfoForm):
    """ Form for teacher profiles """
    def __init__(self, *args, **kwargs):
        super(TeacherProfileForm, self).__init__(*args, **kwargs)
        for field_name in [x.strip().lower() for x in Tag.getTag('teacher_profile_hide_fields').split(',')]:
            if field_name in self.fields and field_name not in _undeletable_fields_all + _undeletable_fields_teachers:
                del self.fields[field_name]

# A list of guardian fields that can not be deleted via profile_hide_fields tags
_undeletable_fields_guardians = []
class GuardianProfileForm(UserContactForm, GuardianInfoForm):
    """ Form for guardian profiles """
    def __init__(self, *args, **kwargs):
        super(GuardianProfileForm, self).__init__(*args, **kwargs)
        for field_name in [x.strip().lower() for x in Tag.getTag('guardian_profile_hide_fields').split(',')]:
            if field_name in self.fields and field_name not in _undeletable_fields_all + _undeletable_fields_guardians:
                del self.fields[field_name]

# A list of educator fields that can not be deleted via profile_hide_fields tags
_undeletable_fields_educators = []
class EducatorProfileForm(UserContactForm, EducatorInfoForm):
    """ Form for educator profiles """
    def __init__(self, *args, **kwargs):
        super(EducatorProfileForm, self).__init__(*args, **kwargs)
        for field_name in [x.strip().lower() for x in Tag.getTag('educator_profile_hide_fields').split(',')]:
            if field_name in self.fields and field_name not in _undeletable_fields_all + _undeletable_fields_educators:
                del self.fields[field_name]

# A list of volunteer fields that can not be deleted via profile_hide_fields tags
_undeletable_fields_volunteers = []
class VolunteerProfileForm(UserContactForm):
    def __init__(self, *args, **kwargs):
        super(VolunteerProfileForm, self).__init__(*args, **kwargs)
        for field_name in [x.strip().lower() for x in Tag.getTag('volunteer_profile_hide_fields').split(',')]:
            if field_name in self.fields and field_name not in _undeletable_fields_all + _undeletable_fields_volunteers:
                del self.fields[field_name]

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
    address_country = forms.ChoiceField(required=False, choices=[('', '(select a country)')] + sorted(country_names.items(), key = lambda x: x[1]), widget=forms.Select(attrs={'class': 'input-medium hidden'}))
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
