from django import forms
from esp.db.forms import AjaxForeignKeyNewformField
from esp.users.models import ESPUser

class GenericSearchForm(forms.Form):
    target_user = AjaxForeignKeyNewformField(key_type=ESPUser, field_name='target_user', label='Target User',
        help_text='Select a user.')

class TeacherSearchForm(forms.Form):
    target_user = AjaxForeignKeyNewformField(key_type=ESPUser, field_name='target_user', label='Target Teacher',
        help_text='Select a teacher.', ajax_func='ajax_autocomplete_teacher')

class StudentSearchForm(forms.Form):
    target_user = AjaxForeignKeyNewformField(key_type=ESPUser, field_name='target_user', label='Target Student',
        help_text='Select a student.', ajax_func='ajax_autocomplete_student')