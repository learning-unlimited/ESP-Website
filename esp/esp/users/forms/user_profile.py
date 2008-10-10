import django.forms as forms
import re

_phone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
_localphone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
_states = ['AL' , 'AK' , 'AR', 'AZ' , 'CA' , 'CO' , 'CT' , 'DC' , 'DE' , 'FL' , 'GA' , 'GU' , 'HI' , 'IA' , 'ID'  ,'IL','IN'  ,'KS'  ,'KY'  ,'LA'  ,'MA' ,'MD'  ,'ME'  ,'MI'  ,'MN'  ,'MO' ,'MS'  ,'MT'  ,'NC'  ,'ND' ,'NE'  ,'NH'  ,'NJ'  ,'NM' ,'NV'  ,'NY' ,'OH'  , 'OK' ,'OR'  ,'PA'  ,'PR' ,'RI'  ,'SC'  ,'SD'  ,'TN' ,'TX'  ,'UT'  ,'VA'  ,'VI'  ,'VT'  ,'WA'  ,'WI'  ,'WV' ,'WY' ,'Canada']

class PhoneNumberField(forms.RegexField):
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
    def __init__(self, user = None, *args, **kwargs):
        if user is None or not (hasattr(user, 'other_user') and user.other_user):
            self.makeRequired = True
        else:
            self.makeRequired = False
	self.base_fields['first_name'] = forms.CharField(max_length=64, required=self.makeRequired)
	self.base_fields['first_name'].widget.attrs['size'] = 25
	self.base_fields['last_name'] = forms.CharField(max_length=64, required=self.makeRequired)
	self.base_fields['last_name'].widget.attrs['size'] = 30
	self.base_fields['e_mail'] = forms.EmailField(required=self.makeRequired)
	self.base_fields['e_mail'].widget.attrs['size'] = 25
	self.base_fields['phone_day'] = PhoneNumberField(local_areacode='617', required=self.makeRequired)
	self.base_fields['phone_cell'] = PhoneNumberField(local_areacode='617', required=False)
	self.base_fields['address_street'] = forms.CharField(max_length=100, required=self.makeRequired)
	self.base_fields['address_street'].widget.attrs['size'] = 40
	self.base_fields['address_city'] = forms.CharField(max_length=50, required=self.makeRequired)
	self.base_fields['address_city'].widget.attrs['size'] = 20
	self.base_fields['address_state'] = forms.ChoiceField(choices=zip(_states,_states), required=self.makeRequired)
	self.base_fields['address_zip'] = forms.CharField(max_length=5, required=self.makeRequired)
	self.base_fields['address_zip'].widget.attrs['size'] = 5
	#forms.HiddenField(field_name="address_postal",is_required=False), # ???

	forms.Form.__init__(self, user, *args, **kwargs)

    ####
    ###phone_validators = [OneOfSetAreFilled(['phone_day','phone_cell'])]

class TeacherContactForm(UserContactForm):
    def __init__(self, user = None, *args, **kwargs):
	UserContactForm.__init__(self, user, *args, **kwargs)
	self.base_fields['phone_cell'].required = self.makeRequired
    
class EmergContactForm(forms.Form):
    def __init__(self, user = None, *args, **kwargs):
	# Copy entries
	leech = UserContactForm(user, *args, **kwargs)
	#del leech.base_fields['address_postal']
	for k,v in leech.base_fields.iteritems():
	    self.base_fields['emerg_'+k] = v
	self.makeRequired = leech.makeRequired

	forms.Form.__init__(self, user, *args, **kwargs)

class GuardContactForm(forms.Form):
    def __init__(self, user = None, *args, **kwargs):
	# Copy entries
	leech = UserContactForm(user, *args, **kwargs)
	del leech.base_fields['address_street']
	del leech.base_fields['address_city']
	del leech.base_fields['address_zip']
	#del leech.base_fields['address_postal']
	for k,v in leech.base_fields.iteritems():
	    self.base_fields['guard_'+k] = v
	self.makeRequired = leech.makeRequired

	forms.Form.__init__(self, user, *args, **kwargs)

class StudentInfoForm(forms.Form):
    def __init__(self, user = None, *args, **kwargs):
        from esp.users.models import ESPUser
        if user is None or not (hasattr(user, 'other_user') and user.other_user):
            makeRequired = True
        else:
            makeRequired = False
	
        import datetime
        from esp.users.models import shirt_sizes, shirt_types

class TeacherInfoForm(forms.Form):
    def __init__(self, user = None, *args, **kwargs):
	pass

class EducatorInfoForm(forms.Form):
    def __init__(self, user = None, *args, **kwargs):
	pass

class GuardianInfoForm(forms.Form):
    def __init__(self, user = None, *args, **kwargs):
	pass

class StudentProfileForm(UserContactForm, EmergContactForm, GuardContactForm, StudentInfoForm):
    def __init__(self, user = None, *args, **kwargs):
	pass
class TeacherProfileForm(TeacherContactForm, TeacherInfoForm):
    def __init__(self, user = None, *args, **kwargs):
	pass
class GuardianProfileForm(UserContactForm, GuardianInfoForm):
    def __init__(self, user = None, *args, **kwargs):
	pass
class EducatorProfileForm(UserContactForm, EducatorInfoForm):
    def __init__(self, user = None, *args, **kwargs):
	pass
