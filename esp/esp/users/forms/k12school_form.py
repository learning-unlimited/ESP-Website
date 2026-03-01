from django import forms
from esp.users.models import K12School, ContactInfo
from esp.db.forms import AjaxForeignKeyNewformField

class K12SchoolForm(forms.ModelForm):
    """
    A form for creating K12School objects from the frontend.
    """
    contact = AjaxForeignKeyNewformField(
        key_type=ContactInfo,
        field_name='contact',
        required=False,
        label='Contact Info',
        help_text='A set of contact information for this school. Type to search by name (Last, First), or go edit a new one.'
    )

    class Meta:
        model = K12School
        fields = [
            'name',
            'contact',
            'school_type',
            'grades',
            'school_id',
            'contact_title'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True

        # Force single-line inputs for everything, rather than giant textareas
        for _field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget = forms.TextInput()
            field.widget.attrs['class'] = 'input-xlarge'
