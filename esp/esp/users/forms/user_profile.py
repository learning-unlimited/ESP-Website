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

class PhoneNumberField(forms.RegexField):
    """ Field for phone number. If area code not given, local_areacode is used instead. """
    def __init__(self, length=12, max_length=14, local_areacode = None, *args, **kwargs):
        forms.RegexField.__init__(self, regex=_phone_re, max_length=14, *args, **kwargs)
        self.widget.attrs['size'] = length
        self.areacode = local_areacode

    def clean(self, value):
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

# TODO: Try to adapt some of these for ModelForm?
class UserContactForm(forms.Form):
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

    def __init__(self, user = None, *args, **kwargs):
        if user is None or not (hasattr(user, 'other_user') and user.other_user):
            self.makeRequired = True
        else:
            self.makeRequired = False
        # set a few things...
        self.base_fields['e_mail'].widget.attrs['size'] = 25

        # GAH!
        for field in self.base_fields.itervalues():
            if field.required:
                field.required = self.makeRequired

        # Restore oldforms thing
        for field in self.base_fields.itervalues():
            if field.required:
                field.widget.attrs['class'] = 'required'

        super(UserContactForm, self).__init__(self, *args, **kwargs)

    def clean_phone_cell(self):
        if not self.cleaned_data.has_key('phone_day') and not self.cleaned_data.has_key('phone_cell'):
            raise ValidationError("Please provide either a day phone or cell phone.")

class TeacherContactForm(UserContactForm):
    """ Contact form for teachers """
    phone_cell = PhoneNumberField(local_areacode='617')
    def __init__(self, *args, **kwargs):
        super(TeacherContactForm, self).__init__(self, *args, **kwargs)
    
class EmergContactForm(forms.Form):
    """ Contact form for emergency contacts """
    def __init__(self, *args, **kwargs): # TODO: do I need to explicitly list user as argument?
        # Copy entries
        leech = UserContactForm(*args, **kwargs)
        for k,v in leech.base_fields.iteritems():
            self.base_fields['emerg_'+k] = v
        self.makeRequired = leech.makeRequired

        super(EmergContactForm, self).__init__(self, *args, **kwargs)

class GuardContactForm(forms.Form):
    """ Contact form for guardians """
    def __init__(self, *args, **kwargs):
        # Copy entries
        leech = UserContactForm(*args, **kwargs)
        for k,v in leech.base_fields.iteritems():
            self.base_fields['guard_'+k] = v
        del self.base_fields['guard_address_street']
        del self.base_fields['guard_address_city']
        del self.base_fields['guard_address_zip']
        self.makeRequired = leech.makeRequired

        super(GuardContactForm, self).__init__(self, *args, **kwargs)

class StudentInfoForm(forms.Form):
    """ Extra student-specific information """
    from esp.users.models import ESPUser
    from esp.users.models import shirt_sizes, shirt_types

    graduation_year = forms.ChoiceField(choices=[(str(ESPUser.YOGFromGrade(x)), str(x)) for x in range(7,13)])
    school = forms.CharField(max_length=128)
    dob = None #FIXME!!!!
    studentrep = forms.BooleanField(required=False)
    studentrep_expl = forms.CharField(required=False)
    shirt_size = forms.ChoiceField(choices=([('','')]+list(shirt_sizes)), required=False)
    shirt_type = forms.ChoiceField(choices=([('','')]+list(shirt_types)), required=False)

    def __init__(self, user = None, *args, **kwargs):
        from esp.users.models import ESPUser
        if user is None or not (hasattr(user, 'other_user') and user.other_user):
            makeRequired = True
        else:
            makeRequired = False

        # Set widget stuff
        self.base_fields['school'].widget.attrs['size'] = 24
        self.base_fields['studentrep_expl'].widget = forms.Textarea()
        self.base_fields['studentrep_expl'].widget.attrs['rows'] = 8
        self.base_fields['studentrep_expl'].widget.attrs['cols'] = 45

        # GAH!
        for field in self.base_fields.itervalues():
            if field.required:
                field.required = makeRequired

        # Restore oldforms thing
        for field in self.base_fields.itervalues():
            if field.required:
                field.widget.attrs['class'] = 'required'

        super(StudentInfoForm, self).__init__(*args, **kwargs)

    def clean_studentrep_expl(self):
        # TODO: run if blank?
        if self.cleaned_data['studentrep'] and not self.cleaned_data.has_key('studentrep_expl'):
            raise ValidationError("Please enter an explanation above.")


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

