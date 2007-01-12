from django import forms
from django.core import validators

class UserContactManipulator(forms.Manipulator):
    """Manipulator for User Contact information """
    def __init__(self):
        self.fields = (
            forms.TextField(field_name="full_name", length=20, maxlength=256, is_required=True),
            forms.DateField(field_name="dob", is_required=True),
            forms.EmailField(field_name="e_mail", is_required=True),
            forms.PhoneNumberField(field_name="phone_day", is_required=True),
            forms.PhoneNumberField(field_name="phone_cell", is_required=True),
            forms.PhoneNumberField(field_name="phone_even", is_required=True),
            forms.TextField(field_name="address_street", length=40, maxlength=100, is_required=True),
            forms.TextField(field_name="address_city", length=40, maxlength=50, is_required=True),
            USStateSelectField(field_name="address_state", is_required=True),
            forms.TextField(field_name="address_zip", length=5, maxlength=5, is_required=True)
        )
        
class EmergContactManipulator(forms.Manipulator):
    """Manipulator for User Contact information """
    def __init__(self):
        self.fields = (
            forms.TextField(field_name="emerg_full_name", length=20, maxlength=256, is_required=True),
            forms.DateField(field_name="emerg_dob", is_required=False),
            forms.EmailField(field_name="emerg_e_mail", is_required=True),
            forms.PhoneNumberField(field_name="emerg_phone_day", is_required=True),
            forms.PhoneNumberField(field_name="emerg_phone_cell", is_required=True),
            forms.PhoneNumberField(field_name="emerg_phone_even", is_required=True),    
            forms.TextField(field_name="emerg_address_street", length=40, maxlength=100, is_required=True),
            forms.TextField(field_name="emerg_address_city", length=40, maxlength=50, is_required=True),
            USStateSelectField(field_name="emerg_address_state", is_required=True),
            forms.TextField(field_name="emerg_address_zip", length=5, maxlength=5, is_required=True)
        )         
            
class GuardContactManipulator(forms.Manipulator):
    """Manipulator for User Contact information """
    def __init__(self):
        self.fields = (
            forms.TextField(field_name="guard_full_name", length=20, maxlength=256, is_required=True),
            forms.DateField(field_name="guard_dob", is_required=False),
            forms.EmailField(field_name="guard_e_mail", is_required=True),
            forms.PhoneNumberField(field_name="guard_phone_day", is_required=True),
            forms.PhoneNumberField(field_name="guard_phone_cell"),
            forms.PhoneNumberField(field_name="guard_phone_even"),
            )

class StudentInfoManipulator(forms.Manipulator):
    """ Manipulator for student info """
    def __init__(self):
        import datetime
        cur_year = datetime.date.today().year
        
        self.fields = (
            forms.SelectField(field_name="graduation_year", choices=zip(range(cur_year,cur_year+20),range(cur_year,cur_year+20)), is_required=True),
            forms.TextField(field_name="school", length=24, maxlength=128)
            )

class TeacherInfoManipulator(forms.Manipulator):
    """ Manipulator for Teacher info """
    def __init__(self):
        self.fields = (
            forms.SelectField(field_name="graduation_year", choices=(('',''))+zip(range(cur_year,cur_year+20),range(cur_year,cur_year+20)), is_required=True),
            forms.TextField(field_name="school", length=24, maxlength=128),
            forms.TextField(field_name="major", length=10, maxlength=32)
            )

class EducatorInfoManipulator(forms.Manipulator):
    """ Manipulator for Educator Info """
    def __init__(self):
        self.fields = (
            forms.TextField(field_name="subject_taught", length=12, maxlength=64),
            forms.TextField(field_name="grades_taught", length=10, maxlength=16),
            forms.TextField(field_name="school", length=24, maxlength=128)
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
    
class USStateSelectField(forms.SelectField):
    def __init__(self, field_name, is_required=False, validator_list=None, member_name = None):
        states = ['AL' , 'AK' , 'AR', 'AZ' , 'CA' , 'CO' , 'CT' , 'DC' , 'DE' , 'FL' , 'GA' , 'GU' , 'HI' , 'IA' , 'ID'  ,'IL','IN'  ,'KS'  ,'KY'  ,'LA'  ,'MA' ,'MD'  ,'ME'  ,'MI'  ,'MN'  ,'MO' ,'MS'  ,'MT'  ,'NC'  ,'ND' ,'NE'  ,'NH'  ,'NJ'  ,'NM' ,'NV'  ,'NY' ,'OH'  , 'OK' ,'OR'  ,'PA'  ,'PR' ,'RI'  ,'SC'  ,'SD'  ,'TN' ,'TX'  ,'UT'  ,'VA'  ,'VI'  ,'VT'  ,'WA'  ,'WI'  ,'WV' ,'WY' ,'Canada']
        choices = zip(states, states)
        blah = forms.SelectField(field_name = field_name, validator_list = validator_list, member_name = member_name, choices = choices)
        self.__dict__ =  blah.__dict__
        
        
