from django import forms
from django.core import validators
import re

class UserContactManipulator(forms.Manipulator):
    """Manipulator for User Contact information """
    def __init__(self):
        phone_validators = [OneOfSetAreFilled(['phone_day','phone_even','phone_cell'])]
        self.fields = (
            forms.TextField(field_name="first_name", length=15, maxlength=64, is_required=True, validator_list=[validators.isNotEmpty]),
            forms.TextField(field_name="last_name", length=15, maxlength=64, is_required=False, validator_list=[validators.isNotEmpty]),            
            forms.EmailField(field_name="e_mail", is_required=True, length=25, validator_list=[validators.isNotEmpty]),
            ESPPhoneNumberField(field_name="phone_day", local_areacode='617', is_required=True),
            ESPPhoneNumberField(field_name="phone_cell", local_areacode='617'),
            ESPPhoneNumberField(field_name="phone_even", local_areacode='617'),
            forms.TextField(field_name="address_street", length=20, maxlength=100, is_required=True, validator_list=[validators.isNotEmpty]),
            forms.TextField(field_name="address_city", length=20, maxlength=50, is_required=True, validator_list=[validators.isNotEmpty]),
            USStateSelectField(field_name="address_state", is_required=True),
            forms.TextField(field_name="address_zip", length=5, maxlength=5, is_required=True, validator_list=[validators.isNotEmpty])
        )
        
class EmergContactManipulator(forms.Manipulator):
    """Manipulator for User Contact information """
    def __init__(self):
        self.fields = (
            forms.TextField(field_name="emerg_first_name", length=15, maxlength=64, is_required=True, validator_list=[validators.isNotEmpty]),
            forms.TextField(field_name="emerg_last_name", length=15, maxlength=64, is_required=False, validator_list=[validators.isNotEmpty]),            
            forms.EmailField(field_name="emerg_e_mail", is_required=True, length=25),
            ESPPhoneNumberField(field_name="emerg_phone_day", is_required=True, local_areacode='617'),
            ESPPhoneNumberField(field_name="emerg_phone_cell", local_areacode='617'),
            ESPPhoneNumberField(field_name="emerg_phone_even", local_areacode='617'),    
            forms.TextField(field_name="emerg_address_street", length=20, maxlength=100, is_required=True, validator_list=[validators.isNotEmpty]),
            forms.TextField(field_name="emerg_address_city", length=20, maxlength=50, is_required=True, validator_list=[validators.isNotEmpty]),
            USStateSelectField(field_name="emerg_address_state", is_required=True),
            forms.TextField(field_name="emerg_address_zip", length=5, maxlength=5, is_required=True, validator_list=[validators.isNotEmpty])
        )

class GuardContactManipulator(forms.Manipulator):
    """Manipulator for User Contact information """
    def __init__(self):
        self.fields = (
            forms.TextField(field_name="guard_first_name", length=15, maxlength=64, is_required=True, validator_list=[validators.isNotEmpty]),
            forms.TextField(field_name="guard_last_name", length=15, maxlength=64, is_required=False, validator_list=[validators.isNotEmpty]),
            forms.EmailField(field_name="guard_e_mail", is_required=True, length=25),
            ESPPhoneNumberField(field_name="guard_phone_day", is_required=True, local_areacode='617'),
            ESPPhoneNumberField(field_name="guard_phone_cell", local_areacode='617'),
            ESPPhoneNumberField(field_name="guard_phone_even", local_areacode='617'),
            )

class StudentInfoManipulator(forms.Manipulator):
    """ Manipulator for student info """
    def __init__(self):
        import datetime
        cur_year = datetime.date.today().year
        
        self.fields = (
            forms.SelectField(field_name="graduation_year", choices=zip(range(cur_year,cur_year+20),range(cur_year,cur_year+20)), is_required=True),
            forms.TextField(field_name="school", length=24, maxlength=128),
            DojoDatePickerField(field_name="dob", is_required=True, default='1994-02-29')
            )


class TeacherInfoManipulator(forms.Manipulator):
    """ Manipulator for Teacher info """
    def __init__(self):
        import datetime
        cur_year = datetime.date.today().year
        self.fields = (
            forms.PositiveIntegerField(field_name="graduation_year", length=4, maxlength=4),
            forms.TextField(field_name="school", length=24, maxlength=128),
            forms.TextField(field_name="major", length=10, maxlength=32),
            DojoDatePickerField(field_name="dob", is_required=False, default='1994-02-29'),
            forms.LargeTextField(field_name="bio", is_required=True, validator_list=[validators.isNotEmpty])
            )

class EducatorInfoManipulator(forms.Manipulator):
    """ Manipulator for Educator Info """
    def __init__(self):
        self.fields = (
            forms.TextField(field_name="subject_taught", length=12, maxlength=64),
            forms.TextField(field_name="grades_taught", length=10, maxlength=16),
            forms.TextField(field_name="school", length=24, maxlength=128),
            forms.TextField(field_name="position", length=10, maxlength=32)
            )
        
class GuardianInfoManipulator(forms.Manipulator):
    """ Manipulator for Educator Info """
    def __init__(self):
        self.fields = (
            forms.PositiveIntegerField(field_name="year_finished", length=4, maxlength=4),
            forms.PositiveIntegerField(field_name="num_kids", length=3, maxlength=16)
            )

class StudentProfileManipulator(forms.Manipulator):
    """ Create the student profile manipulator from the other manipulators """
    def __init__(self):
        self.fields = UserContactManipulator().fields + EmergContactManipulator().fields + GuardContactManipulator().fields + StudentInfoManipulator().fields
        
class TeacherProfileManipulator(forms.Manipulator):
    """ The teacher profile manipulator created from other manipulators """
    def __init__(self):
        self.fields = UserContactManipulator().fields + EmergContactManipulator().fields + TeacherInfoManipulator().fields

class GuardianProfileManipulator(forms.Manipulator):
    """ The guardian profile manipulator created from other manipulators """
    def __init__(self):
        self.fields = UserContactManipulator().fields + GuardianInfoManipulator().fields

class EducatorProfileManipulator(forms.Manipulator):
    """ The educator profile manipulator created from other manipulators """
    def __init__(self):
        self.fields = UserContactManipulator().fields + EducatorInfoManipulator().fields

def YOGValidator(self, field_data, all_data):
    import datetime
    begin_year = datetime.date.today().year
    end_year = datetime.date.today().year + 20
    if type(field_data) != int or field_data < begin_year or field_data > end_year:
        raise validators.ValidationError("Please enter a valid year between "+begin_year+" and "+year)

class OneOfSetAreFilled(object):
    """ This will be valid if at least one of a set of fields are filled in and not empty. """
    def __init__(self, field_list):
        self.field_list = field_list

    def __call__(self, field_data, all_data):
        atleastOne = False
        for field in self.field_list:
            if all_data.get(field, False) and all_data[field][0].strip() != '':
                atleastOne = True
                
        if not atleastOne:
            raise validators.ValidationError, 'At least one of the these fields must be filled in.'

class DojoDatePickerField(forms.DateField):
    """ A pretty dojo date picker field """
    def __init__(self, field_name, length=10, maxlength=10, is_required=False, validator_list=None, member_name=None, default=''):
        if validator_list is None: validator_list = []
        self.field_name = field_name
        self.length, self.maxlength = length, maxlength
        self.is_required = is_required
        self.validator_list = [self.isValidDate] + validator_list
        self.default = default
        if member_name != None:
            self.member_name = member_name

    def render(self, data):
    
        maxlength = ''
        if data is None or data == '':
            initdata = 'value="%s" ' % self.default
        else:
            initdata = 'value="%s" ' % data
            
        if self.maxlength is not None:
            maxlength = 'maxlength="%s" ' % self.maxlength
        
        dojojs = '<script type="text/javascript">dojo.require("dojo.widget.DropdownDatePicker");dojo.require("dojo.widget.Button");</script>'

        return dojojs + "\n" + '<input name="%s" id="%s" class="v%s%s" containerToggle="wipe" containerToggleDuration="300" dojoType="dropdowndatepicker" saveFormat="yyyy-MM-dd" displayFormat="yyyy-MM-dd" %slang="en-us" %s/>' % \
               (self.field_name, self.get_id(), self.__class__.__name__, self.is_required and ' required' or '', initdata, maxlength)
    
        
    
class USStateSelectField(forms.SelectField):
    def __init__(self, field_name, is_required=False, validator_list=None, member_name = None):
        states = ['AL' , 'AK' , 'AR', 'AZ' , 'CA' , 'CO' , 'CT' , 'DC' , 'DE' , 'FL' , 'GA' , 'GU' , 'HI' , 'IA' , 'ID'  ,'IL','IN'  ,'KS'  ,'KY'  ,'LA'  ,'MA' ,'MD'  ,'ME'  ,'MI'  ,'MN'  ,'MO' ,'MS'  ,'MT'  ,'NC'  ,'ND' ,'NE'  ,'NH'  ,'NJ'  ,'NM' ,'NV'  ,'NY' ,'OH'  , 'OK' ,'OR'  ,'PA'  ,'PR' ,'RI'  ,'SC'  ,'SD'  ,'TN' ,'TX'  ,'UT'  ,'VA'  ,'VI'  ,'VT'  ,'WA'  ,'WI'  ,'WV' ,'WY' ,'Canada']
        choices = zip(states, states)
        blah = forms.SelectField(field_name = field_name, validator_list = validator_list, member_name = member_name, choices = choices, is_required = is_required)
        self.__dict__ =  blah.__dict__
        

class ESPPhoneNumberField(forms.TextField):
    phone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
    localphone_re = re.compile(r'^\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*(\d)\D*$')
    
    def __init__(self, field_name, is_required=False, validator_list=None, member_name = None, length=12, maxlength=14, local_areacode = None):
        if validator_list is None:
            validator_list = []
        validator_list = validator_list + [self.isESPPhone]
        blah = forms.TextField(field_name = field_name, validator_list = validator_list, member_name = member_name, is_required = is_required, length = length, maxlength = maxlength)
        self.__dict__ = blah.__dict__
        self.__class__.areacode = local_areacode

    def isESPPhone(self, data, form):
        from django.utils.translation import gettext
        if not self.phone_re.search(data):
            # Try local as well if the area code was supplied
            if self.__class__.areacode is None or not self.localphone_re.search(data):
                raise validators.ValidationError, gettext('Phone numbers must be a valid US number. "%s" is invalid.') % data
#    isESPPhone = staticmethod(isESPPhone)
    
    def html2python(data):
        """ Hook for rewriting phone into proper format """
        newnumber = ''
        if ESPPhoneNumberField.phone_re.search(data):
            numbers = ESPPhoneNumberField.phone_re.match(data).groups()
            newnumber = "".join(numbers[:3]) + '-' + "".join(numbers[3:6]) + '-' + "".join(numbers[6:])
        else:
            if ESPPhoneNumberField.areacode is not None and ESPPhoneNumberField.localphone_re.search(data):
                numbers = ESPPhoneNumberField.localphone_re.match(data).groups()
                newnumber = ESPPhoneNumberField.areacode + '-' + "".join(numbers[:3]) + '-' + "".join(numbers[3:])
        return newnumber
    html2python = staticmethod(html2python)


def isValidSATSectionScore(data, form):
    data = int(data)
    if data < 200 or data > 800:
        raise validators.ValidationError, '"%s" not a valid SAT score.' % data

def isValidSATScore(data, form):
    data = int(data)
    if data < 600 or data > 2400:
        raise validators.ValidationError, '"%s" not a valid SAT score.' % data        



class SATPrepInfoManipulator(forms.Manipulator):
    def __init__(self):
        self.fields = (
            forms.PositiveIntegerField(field_name="old_math_score", length=3, maxlength=3, validator_list=[isValidSATSectionScore]),
            forms.PositiveIntegerField(field_name="old_verb_score", length=3, maxlength=3, validator_list=[isValidSATSectionScore]),
            forms.PositiveIntegerField(field_name="old_writ_score", length=3, maxlength=3, validator_list=[isValidSATSectionScore]),
            forms.TextField(field_name="heard_by", length=24, maxlength=128)
            )


class SATPrepTeacherInfoManipulator(forms.Manipulator):
    def __init__(self, subjects):
        self.fields = (
            forms.PositiveIntegerField(field_name="sat_math", length=3, maxlength=3, validator_list=[isValidSATSectionScore]),
            forms.PositiveIntegerField(field_name="sat_verb", length=3, maxlength=3, validator_list=[isValidSATSectionScore]),
            forms.PositiveIntegerField(field_name="sat_writ", length=3, maxlength=3, validator_list=[isValidSATSectionScore]),
            forms.SelectField(field_name="subject", is_required=True, choices=subjects)
            )
