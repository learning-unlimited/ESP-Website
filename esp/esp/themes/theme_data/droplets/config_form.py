from django import forms
from django.utils.safestring import mark_safe

from esp.themes.forms import ThemeConfigurationForm
from esp.utils.widgets import NavStructureWidgetWithIcons, ContactFieldsWidget

class ConfigForm(ThemeConfigurationForm):
    titlebar_prefix = forms.CharField()
    full_group_name = forms.CharField()
    show_group_name = forms.BooleanField(initial = True, required = False, help_text='Should the full group name be shown in the navigation bar?')
    show_logo_navbar = forms.BooleanField(initial = True, required = False, help_text=mark_safe('Should the logo be shown in the <b>navigation bar</b>?'))
    show_logo_header = forms.BooleanField(initial = True, required = False, help_text=mark_safe('Should the logo be shown in the <b>header banner</b>?'))
    show_header_home = forms.BooleanField(initial = True, required = False, help_text=mark_safe('Should the header banner be shown on the <b>homepage</b>?'))
    show_header_other = forms.BooleanField(initial = True, required = False, help_text=mark_safe('Should the header banner be shown on <b>non-homepage pages</b>?'))
    contact_info = forms.CharField(required = False, widget=forms.Textarea,
                                   help_text='Generic text to include in the "About Us" dropdown in the navigation bar. Leave blank to omit this field.')
    show_email = forms.BooleanField(required = False, help_text='Should the group email address be shown in the "About Us" dropdown in the navigation bar?')
    contact_links = forms.Field(required = False, widget=ContactFieldsWidget,
                                label='Contact links below contact info (use absolute or relative URLs)',
                                initial=[{"text": "contact us", "link": "/contact.html"}])
    nav_structure = forms.Field(widget=NavStructureWidgetWithIcons,
                                help_text="Note: If the first 5 characters of a user's request path match the first 5 characters of\
                                           a header's link, then that header will be highlighted.")
    faq_link = forms.CharField(required=False, initial='/faq.html',
                               help_text='Supply this to link to an FAQ page in the "About Us" dropdown in the navigation bar. Leave blank to omit an FAQ link.')
    facebook_link = forms.URLField(required=False, help_text='Supply this to link to Facebook in the "About Us" dropdown in the navigation bar. Leave blank to omit a Facebook link.')
    # URLField requires an absolute URL, here we probably want relative.
    show_footer_textbox = forms.BooleanField(initial = False, required = False,
                                             help_text='Should there be an editable text field in the footer?')
