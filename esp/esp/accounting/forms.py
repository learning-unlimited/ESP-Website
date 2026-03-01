from __future__ import absolute_import
from django import forms
from esp.program.models import Program
from esp.db.forms import AjaxForeignKeyNewformField
from esp.users.models import ESPUser


class RefundSearchForm(forms.Form):
    """Form for selecting a program and searching for students to refund."""
    program = forms.ModelChoiceField(
        queryset=Program.objects.all().order_by('-id'),
        label='Program',
        help_text='Select the program for which to issue refunds.',
        empty_label='-- Select a program --',
    )
    target_user = AjaxForeignKeyNewformField(
        key_type=ESPUser,
        field_name='target_user',
        label='Student',
        help_text='Search for a student to refund.',
        ajax_func='ajax_autocomplete_student',
    )
