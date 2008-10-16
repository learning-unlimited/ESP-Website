import django.forms as forms
import re

# SRC: esp/program/manipulators.py

_phone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
_localphone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
_states = ['AL' , 'AK' , 'AR', 'AZ' , 'CA' , 'CO' , 'CT' , 'DC' , 'DE' , 'FL' , 'GA' , 'GU' , 'HI' , 'IA' , 'ID'  ,'IL','IN'  ,'KS'  ,'KY'  ,'LA'  ,'MA' ,'MD'  ,'ME'  ,'MI'  ,'MN'  ,'MO' ,'MS'  ,'MT'  ,'NC'  ,'ND' ,'NE'  ,'NH'  ,'NJ'  ,'NM' ,'NV'  ,'NY' ,'OH'  , 'OK' ,'OR'  ,'PA'  ,'PR' ,'RI'  ,'SC'  ,'SD'  ,'TN' ,'TX'  ,'UT'  ,'VA'  ,'VI'  ,'VT'  ,'WA'  ,'WI'  ,'WV' ,'WY' ,'Canada']

class SizedCharField(forms.CharField):
    """ Just like CharField, but you can set the width of the text widget. """
    def __init__(self, length=None, *args, **kwargs):
        forms.CharField.__init__(self, *args, **kwargs)
        self.widget.attrs['size'] = length

class PhoneNumberField(forms.CharField):
    """ Field for phone number. If area code not given, local_areacode is used instead. """
    def __init__(self, length=12, max_length=14, local_areacode = None, *args, **kwargs):
        forms.CharField.__init__(self, max_length=max_length, *args, **kwargs)
        self.widget.attrs['size'] = length
        self.areacode = local_areacode

    def clean(self, value):
        if value == '':
            return ''
        m = _phone_re.match(value)
        if m:
            numbers = m.groups()
            value = "".join(numbers[:3]) + '-' + "".join(numbers[3:6]) + '-' + "".join(numbers[6:])
            return value

        if self.areacode is not None:
            m = _localphone_re.match(value)
            if m:
                numbers = m.groups()
                value = self.areacode + '-' + "".join(numbers[:3]) + '-' + "".join(numbers[3:])
                return value
        raise forms.ValidationError('Phone numbers must be a valid US number. "%s" is invalid.' % value)

#### NOTE: Python super() does weird things (it's the next in the MRO, not a superclass).
#### DO NOT OMIT IT if overriding __init__() when subclassing these forms

class FormWithRequiredCss(forms.Form):
    """ Form that adds the "required" class to every required widget, to restore oldforms behavior. """
    def __init__(self, *args, **kwargs):
        super(FormWithRequiredCss, self).__init__(*args, **kwargs)
        for field in self.fields.itervalues():
            if field.required:
                field.widget.attrs['class'] = 'required'

class FormUnrestrictedOtherUser(FormWithRequiredCss):
    """ Form that implements makeRequired for the old form --- disables required fields at in some cases. """

    def __init__(self, user=None, *args, **kwargs):
        super(FormUnrestrictedOtherUser, self).__init__(*args, **kwargs)
        if user is None or not (hasattr(user, 'other_user') and user.other_user):
            pass
        else:
            for field in self.fields.itervalues():
                if field.required:
                    field.required = False
                    field.widget.attrs['class'] = None # GAH!

# TODO: Try to adapt some of these for ModelForm?
class UserContactForm(FormUnrestrictedOtherUser):
    """ Base for contact form """

    first_name = SizedCharField(length=25, max_length=64)
    last_name = SizedCharField(length=30, max_length=64)
    e_mail = forms.EmailField()
    phone_day = PhoneNumberField(local_areacode='617')
    phone_cell = PhoneNumberField(local_areacode='617', required=False)
    address_street = SizedCharField(length=40, max_length=100)
    address_city = SizedCharField(length=20, max_length=50)
    address_state = forms.ChoiceField(choices=zip(_states,_states))
    address_zip = SizedCharField(length=5, max_length=5)
    address_postal = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.base_fields['e_mail'].widget.attrs['size'] = 25
        super(UserContactForm, self).__init__(self, *args, **kwargs)

    def clean_phone_cell(self):
        if self.cleaned_data['phone_day'] == '' and self.cleaned_data['phone_cell'] == '':
            raise forms.ValidationError("Please provide either a day phone or cell phone.")

class TeacherContactForm(UserContactForm):
    """ Contact form for teachers """

    phone_cell = PhoneNumberField(local_areacode='617')
    
class EmergContactForm(FormUnrestrictedOtherUser):
    """ Contact form for emergency contacts """

    emerg_first_name = SizedCharField(length=25, max_length=64)
    emerg_last_name = SizedCharField(length=30, max_length=64)
    emerg_e_mail = forms.EmailField(required=False)
    emerg_phone_day = PhoneNumberField(local_areacode='617')
    emerg_phone_cell = PhoneNumberField(local_areacode='617', required=False)
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
    guard_phone_day = PhoneNumberField(local_areacode='617')
    guard_phone_cell = PhoneNumberField(local_areacode='617', required=False)

class StudentInfoForm(FormUnrestrictedOtherUser):
    """ Extra student-specific information """
    from esp.users.models import ESPUser
    from esp.users.models import shirt_sizes, shirt_types

    graduation_year = forms.ChoiceField(choices=[(str(ESPUser.YOGFromGrade(x)), str(x)) for x in range(7,13)])
    school = forms.CharField(max_length=128, required=False)
    dob = None #FIXME!!!!
    studentrep = forms.BooleanField(required=False)
    studentrep_expl = forms.CharField(required=False)
    shirt_size = forms.ChoiceField(choices=([('','')]+list(shirt_sizes)), required=False)
    shirt_type = forms.ChoiceField(choices=([('','')]+list(shirt_types)), required=False)

    def __init__(self, *args, **kwargs):
        # Set widget stuff
        self.base_fields['school'].widget.attrs['size'] = 24
        self.base_fields['studentrep_expl'].widget = forms.Textarea()
        self.base_fields['studentrep_expl'].widget.attrs['rows'] = 8
        self.base_fields['studentrep_expl'].widget.attrs['cols'] = 45

        super(StudentInfoForm, self).__init__(*args, **kwargs)

    def clean_studentrep_expl(self):
        self.cleaned_data['studentrep_expl'] = self.cleaned_data['studentrep_expl'].strip()
        if self.cleaned_data['studentrep'] and self.cleaned_data['studentrep_expl'] == '':
            raise forms.ValidationError("Please enter an explanation above.")


class TeacherInfoForm(forms.Form):
    """ Extra teacher-specific information """

    from esp.users.models import shirt_sizes, shirt_types

    graduation_year = forms.IntegerField(required=False)
    school = SizedCharField(length=24, max_length=128, required=False)
    major = SizedCharField(length=30, max_length=32, required=False)
    shirt_size = forms.ChoiceField(choices=([('','')]+list(shirt_sizes)), required=False)
    shirt_type = forms.ChoiceField(choices=([('','')]+list(shirt_types)), required=False)

    def __init__(self, *args, **kwargs):
        self.base_fields['graduation_year'].widget.attrs['size'] = 4
        self.base_fields['graduation_year'].widget.attrs['maxlength'] = 4
        super(TeacherInfoForm, self).__init__(*args, **kwargs)

class EducatorInfoForm(forms.Form):
    """ Extra educator-specific information """

    subject_taught = SizedCharField(length=12, max_length=64, required=False)
    grades_taught = SizedCharField(length=10, max_length=16, required=False)
    school = SizedCharField(length=24, max_length=128, required=False)
    position = SizedCharField(length=10, max_length=32, required=False)

class GuardianInfoForm(forms.Form):
    """ Extra guardian-specific information """

    year_finished = forms.IntegerField(min_value=1, required=False)
    num_kids = forms.IntegerField(min_value=1, required=False)

    def __init__(self, *args, **kwargs):
        self.base_fields['year_finished'].widget.attrs['size'] = 4
        self.base_fields['year_finished'].widget.attrs['maxlength'] = 4
        self.base_fields['num_kids'].widget.attrs['size'] = 3
        self.base_fields['num_kids'].widget.attrs['maxlength'] = 16
        super(GuardianInfoForm, self).__init__(*args, **kwargs)

class StudentProfileForm(UserContactForm, EmergContactForm, GuardContactForm, StudentInfoForm):
    """ Form for student profiles """

class TeacherProfileForm(TeacherContactForm, TeacherInfoForm):
    """ Form for student profiles """

class GuardianProfileForm(UserContactForm, GuardianInfoForm):
    """ Form for guardian profiles """

class EducatorProfileForm(UserContactForm, EducatorInfoForm):
    """ Form for educator profiles """

