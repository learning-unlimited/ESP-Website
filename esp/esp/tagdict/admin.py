from django import forms
from django.contrib import admin

from esp.admin import admin_site
from esp.tagdict.models import Tag
from esp.tagdict.validators import (
    ALL_HIDE_FIELDS_TAG_KEYS,
    validate_hide_fields_value,
)


class TagAdminForm(forms.ModelForm):
    """ModelForm for Tag that validates *_hide_fields tag values."""

    value = forms.CharField(required=False, widget=forms.Textarea)

    class Meta:
        model = Tag
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        key = cleaned_data.get('key', '')
        value = cleaned_data.get('value', '')

        if key in ALL_HIDE_FIELDS_TAG_KEYS and value:
            result = validate_hide_fields_value(key, value)
            if result is not None:
                _valid_fields, invalid_fields, valid_set = result
                if invalid_fields:
                    raise forms.ValidationError(
                        "The following field name(s) are not valid for "
                        "'%(tag_key)s': %(invalid)s. "
                        "Valid field names are: %(valid)s",
                        params={
                            'tag_key': key,
                            'invalid': ', '.join(invalid_fields),
                            'valid': ', '.join(sorted(valid_set)),
                        },
                        code='invalid_field_names',
                    )

        return cleaned_data


class TagAdmin(admin.ModelAdmin):
    form = TagAdminForm
    list_display = ('key', 'value', 'target', )
    list_filter = ('key', 'object_id', 'content_type__model', )


admin_site.register(Tag, TagAdmin)
