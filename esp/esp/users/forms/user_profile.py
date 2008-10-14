import django.forms as forms
import re

# SRC: esp/program/manipulators.py

_phone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
_localphone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
_states = ['AL' , 'AK' , 'AR', 'AZ' , 'CA' , 'CO' , 'CT' , 'DC' , 'DE' , 'FL' , 'GA' , 'GU' , 'HI' , 'IA' , 'ID'  ,'IL','IN'  ,'KS'  ,'KY'  ,'LA'  ,'MA' ,'MD'  ,'ME'  ,'MI'  ,'MN'  ,'MO' ,'MS'  ,'MT'  ,'NC'  ,'ND' ,'NE'  ,'NH'  ,'NJ'  ,'NM' ,'NV'  ,'NY' ,'OH'  , 'OK' ,'OR'  ,'PA'  ,'PR' ,'RI'  ,'SC'  ,'SD'  ,'TN' ,'TX'  ,'UT'  ,'VA'  ,'VI'  ,'VT'  ,'WA'  ,'WI'  ,'WV' ,'WY' ,'Canada']

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

# TODO: Try to adapt some of these for ModelForm?
class UserContactForm(forms.Form):
    """ Base for contact form """

    first_name = forms.CharField(max_length=64)
    last_name = forms.CharField(max_length=64)
    e_mail = forms.EmailField()
    phone_day = PhoneNumberField(local_areacode='617')
    phone_cell = PhoneNumberField(local_areacode='617', required=False)
    address_street = forms.CharField(max_length=100)
    address_city = forms.CharField(max_length=50)
    address_state = forms.ChoiceField(choices=zip(_states,_states))
    address_zip = forms.CharField(max_length=5)

    def __init__(self, user = None, *args, **kwargs):
        if user is None or not (hasattr(user, 'other_user') and user.other_user):
            self.makeRequired = True
        else:
            self.makeRequired = False
        # set a few things...
        self.base_fields['first_name'].widget.attrs['size'] = 25
        self.base_fields['last_name'].widget.attrs['size'] = 30
        self.base_fields['e_mail'].widget.attrs['size'] = 25
        self.base_fields['address_street'].widget.attrs['size'] = 40
        self.base_fields['address_city'].widget.attrs['size'] = 20
        self.base_fields['address_zip'].widget.attrs['size'] = 5

        # GAH!
        for field in self.base_fields.iteritems():
            if field.required:
                field.required = makeRequired

        # Restore oldforms thing
        for field in self.base_fields.iteritems():
            if field.required:
                field.widget.attrs['class'] = 'required'

        forms.Form.__init__(self, user, *args, **kwargs)

    def clean_phone_cell(self):
        if not self.clean_data.has_key('phone_day') and not self.clean_data.has_key('phone_cell'):
            raise ValidationError("Please provide either a day phone or cell phone.")

class TeacherContactForm(UserContactForm):
    """ Contact form for teachers """
    def __init__(self, user = None, *args, **kwargs):
        self.base_fields['phone_cell'].required = True
        UserContactForm.__init__(self, user, *args, **kwargs)
    
class EmergContactForm(forms.Form):
    """ Contact form for emergency contacts """
    def __init__(self, user = None, *args, **kwargs):
        # Copy entries
        leech = UserContactForm(user, *args, **kwargs)
        for k,v in leech.base_fields.iteritems():
            self.base_fields['emerg_'+k] = v
        self.makeRequired = leech.makeRequired

        forms.Form.__init__(self, user, *args, **kwargs)

class GuardContactForm(forms.Form):
    """ Contact form for guardians """
    def __init__(self, user = None, *args, **kwargs):
        # Copy entries
        leech = UserContactForm(user, *args, **kwargs)
        del leech.base_fields['address_street']
        del leech.base_fields['address_city']
        del leech.base_fields['address_zip']
        for k,v in leech.base_fields.iteritems():
            self.base_fields['guard_'+k] = v
        self.makeRequired = leech.makeRequired

        forms.Form.__init__(self, user, *args, **kwargs)

class StudentInfoForm(forms.Form):
    """ Extra student-specific information """
    def __init__(self, user = None, *args, **kwargs):
        from esp.users.models import ESPUser
        if user is None or not (hasattr(user, 'other_user') and user.other_user):
            makeRequired = True
        else:
            makeRequired = False

        import datetime
        from esp.users.models import shirt_sizes, shirt_types
        cur_year = datetime.date.today().year

        shirt_sizes = [('', '')] + list(shirt_sizes)
        shirt_types = [('', '')] + list(shirt_types)

        #studentrep_explained = NonEmptyIfOtherChecked('studentrep', 'Please enter an explanation above.')
        #studentrep_explained.always_test = True # because validators normally aren't run if a field is blank
        #
        #self.fields = (
            #GraduationYearField(field_name="graduation_year", is_required=makeRequired, choices=[(str(ESPUser.YOGFromGrade(x)), str(x)) for x in range(7,13)]),
            #forms.TextField(field_name="school", length=24, max_length=128),
            #HTMLDateField(field_name="dob", is_required=makeRequired),
            #forms.CheckboxField(field_name="studentrep", is_required=False),
            #forms.LargeTextField(field_name="studentrep_expl", is_required=False, rows=8, cols=45, validator_list=[studentrep_explained]),
            #forms.SelectField(field_name="shirt_size", is_required=False, choices=shirt_sizes, validator_list=[validators.isNotEmpty]),
            #forms.SelectField(field_name="shirt_type", is_required=False, choices=shirt_types, validator_list=[validators.isNotEmpty]),
            #)

class TeacherInfoForm(forms.Form):
    """ Extra teacher-specific information """
    def __init__(self, user = None, *args, **kwargs):
        pass

class EducatorInfoForm(forms.Form):
    """ Extra educator-specific information """
    def __init__(self, user = None, *args, **kwargs):
        pass

class GuardianInfoForm(forms.Form):
    """ Extra guardian-specific information """
    def __init__(self, user = None, *args, **kwargs):
        pass

class StudentProfileForm(UserContactForm, EmergContactForm, GuardContactForm, StudentInfoForm):
    """ Form for student profiles """
    def __init__(self, user = None, *args, **kwargs):
        pass
class TeacherProfileForm(TeacherContactForm, TeacherInfoForm):
    """ Form for student profiles """
    def __init__(self, user = None, *args, **kwargs):
        pass
class GuardianProfileForm(UserContactForm, GuardianInfoForm):
    """ Form for guardian profiles """
    def __init__(self, user = None, *args, **kwargs):
        pass
class EducatorProfileForm(UserContactForm, EducatorInfoForm):
    """ Form for educator profiles """
    def __init__(self, user = None, *args, **kwargs):
        pass
