from django import forms

from esp.accounting.models import LineItemType, LineItemOptions
from esp.program.models import Program

exclude_line_items = ["Sibling discount", "Program admission", "Financial aid grant", "Student payment", "Donation to Learning Unlimited", "Saturday Lunch", "Sunday Lunch"]

class LineItemForm(forms.ModelForm):
    class Meta:
        model = LineItemType
        fields = ('text', 'amount_dec', 'required', 'max_quantity')
        labels = {
            'text': 'Name',
            'amount_dec': 'Cost',
        }
        help_texts = {
            'required': 'Should this line item be automatically added for every student?',
        }
        widgets = {
            'text': forms.TextInput(attrs={'placeholder': '(name)'}),
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
