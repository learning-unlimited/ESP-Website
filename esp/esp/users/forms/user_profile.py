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
    from esp.users.models import ESPUser
    from esp.users.models import shirt_sizes, shirt_types

    graduation_year = forms.ChoiceField(choices=[(str(ESPUser.YOGFromGrade(x)), str(x)) for x in range(7,13)])
    school = forms.CharField(max_length=128)
    dob = None #FIXME!!!!
    studentrep = forms.BooleanField(required=False)
    studentrep_expl = forms.CharField(required=False)
    shirt_size = forms.SelectField(choices=([('','')]+list(shirt_sizes)), required=False)
    shirt_type = forms.SelectField(choices=([('','')]+list(shirt_types)), required=False)

    def __init__(self, user = None, *args, **kwargs):
        from esp.users.models import ESPUser
        if user is None or not (hasattr(user, 'other_user') and user.other_user):
            makeRequired = True
        else:
            makeRequired = False

        shirt_sizes = [('', '')] + list(shirt_sizes)
        shirt_types = [('', '')] + list(shirt_types)

        # Set widget stuff
        self.base_fields['school'].widget.attrs['size'] = 24
        self.base_fields['studentrep_expl'].widget = forms.Textarea()
        self.base_fields['studentrep_expl'].widget.attrs['rows'] = 8
        self.base_fields['studentrep_expl'].widget.attrs['cols'] = 45

        # GAH!
        for field in self.base_fields.iteritems():
            if field.required:
                field.required = makeRequired

        # Restore oldforms thing
        for field in self.base_fields.iteritems():
            if field.required:
                field.widget.attrs['class'] = 'required'

    def clean_studentrep_expl(self):
        # TODO: run if blank?
        if self.clean_data['studentrep'] and not self.has_key['studentrep_expl']:
            raise ValidationError("Please enter an explanation above.")


class TeacherInfoForm(forms.Form):
    """ Extra teacher-specific information """

    from esp.users.models import shirt_sizes, shirt_types

    graduation_year = forms.IntegerField(max_length=4, required=False)
    school = SizedCharField(length=24, max_length=128, required=False)
    major = SizedCharField(length=30, max_length=32, required=False)
    shirt_size = forms.SelectField(choices=([('','')]+list(shirt_sizes)), required=False)
    shirt_type = forms.SelectField(choices=([('','')]+list(shirt_types)), required=False)

    def __init__(self, user = None, *args, **kwargs):
        self.base_fields['graduation_year'].widget.attrs['size'] = 4
        forms.Form.__init__(self, user, *args, **kwargs)

class EducatorInfoForm(forms.Form):
    """ Extra educator-specific information """

    subject_taught = SizedCharField(length=12, max_length=64, required=False)
    grades_taught = SizedCharField(length=10, max_length=16, required=False)
    school = SizedCharField(length=24, max_length=128, required=False)
    position = SizedCharField(length=10, max_length=32, required=False)

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
