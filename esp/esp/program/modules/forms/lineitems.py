from __future__ import absolute_import
from django import forms
from django.core.validators import RegexValidator

from esp.accounting.models import LineItemType, LineItemOptions
from esp.program.models import Program

exclude_line_items = ["Sibling discount", "Program admission", "Financial aid grant", "Student payment", "Donation to Learning Unlimited"]

class LineItemForm(forms.ModelForm):
    text = forms.CharField(label = 'Name', widget = forms.TextInput(attrs={'placeholder': '(name)'}), validators=[RegexValidator(regex = '^(' + '|'.join(exclude_line_items) + ')$', message = 'That line item name is reserved for internal operations. Please choose another name.', inverse_match = True)])
    class Meta:
        model = LineItemType
        fields = ('text', 'amount_dec', 'required', 'max_quantity', 'for_finaid')
        labels = {
            'amount_dec': 'Cost',
        }
        help_texts = {
            'required': 'Should this line item be automatically added for every student?',
            'for_finaid': 'Should financial aid cover this line item? Note that if this is checked, all quantities will be covered up to the max quantity. \
                           If you would like only one instance of this line item to be covered by financial aid, you should set the max quantity to 1 and make \
                           a duplicate line item with a different name and higher max quantity that is not covered by financial aid.'
        }
        widgets = {
            'amount_dec': forms.NumberInput(attrs={'placeholder': '(cost)'}),
        }

OptionFormset = forms.modelformset_factory(
    LineItemOptions,
    fields = ('description', 'amount_dec', 'is_custom'),
    max_num = 1000,
    extra = 0,
    labels = {
        'description': 'Description',
        'amount_dec': 'Cost',
        'is_custom': 'Is custom?'
    },
    help_texts = {
        'amount_dec': 'If blank, takes overall cost',
        'is_custom': 'Should the student be allowed to specify a custom amount for this option?',
    },
    widgets = {
        'description': forms.TextInput(attrs={'placeholder': '(description)'}),
        'amount_dec': forms.NumberInput(attrs={'placeholder': '(cost)'}),
    }
)

class LineItemImportForm(forms.Form):
    program = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        super(LineItemImportForm, self).__init__(*args, **kwargs)
        progs = LineItemType.objects.exclude(text__in=exclude_line_items).values_list('program', flat = True).distinct()
        qs = Program.objects.filter(id__in=progs)
        if cur_prog is not None:
            qs = qs.exclude(id=cur_prog.id)
        self.fields['program'].queryset = qs
