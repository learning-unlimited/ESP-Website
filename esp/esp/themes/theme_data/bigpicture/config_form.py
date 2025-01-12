from __future__ import absolute_import
from django import forms

from esp.themes.forms import ThemeConfigurationForm
from esp.utils.widgets import NavStructureWidgetWithIcons, ContactFieldsWidget

class ConfigForm(ThemeConfigurationForm):
    titlebar_prefix = forms.CharField()
    full_group_name = forms.CharField()
    show_group_name = forms.BooleanField(required = False, help_text='Should the full group name be shown in the page header?')
    show_email = forms.BooleanField(required = False, help_text='Should the group email address be shown in the page header?')
    contact_info = forms.CharField(required = False, widget=forms.Textarea,
                                   help_text='Generic text to include in the page header. Leave blank to omit this field in the header.')
    contact_links = forms.Field(required = False, widget=ContactFieldsWidget,
                                label='Contact links below contact info (use absolute or relative URLs)',
                                initial=[{"text": "contact us", "link": "/contact.html"}])
    nav_structure = forms.Field(widget=NavStructureWidgetWithIcons)
    facebook_link = forms.URLField(required=False, help_text='Leave blank to omit a Facebook link.')
    # URLField requires an absolute URL, here we probably want relative.
    faq_link = forms.CharField(required=False, initial='/faq.html',
                               help_text='Leave blank to omit an FAQ link.')
