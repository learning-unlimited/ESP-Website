from django import forms
from django.utils.safestring import mark_safe

from esp.themes.forms import ThemeConfigurationForm
from esp.utils.widgets import NavStructureWidgetWithIcons, ContactFieldsWidget

class ConfigForm(ThemeConfigurationForm):
    # Display fields
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
    faq_link = forms.CharField(required=False, initial='/faq.html',
                               help_text='Leave blank to omit an FAQ link.')
    show_footer_textbox = forms.BooleanField(initial = False, required = False, help_text='Should there be an editable text field in the footer?')

    # Colors
    accent1 = forms.CharField(label='Primary Accent Color')
    accent2 = forms.CharField(label='Secondary Accent Color')
    navbarBackground = forms.CharField(label='Navbar Background')
    navbarText = forms.CharField(label='Navbar Text Color')
    navbarLinkColor = forms.CharField(label='Navbar Link Color')
    headingColor = forms.CharField(label='Heading Color')
    footerBackground = forms.CharField(label='Footer Background')
    footerText = forms.CharField(label='Footer Text Color')
    footerLinkColor = forms.CharField(label='Footer Link Color')
    linkColor = forms.CharField(label='Body Link Color')
    linkColorHover = forms.CharField(label='Body Link Hover Color')

    # Typography
    h1FontSize = forms.CharField(label='Heading 1 Size (e.g. 42px)')
    h2FontSize = forms.CharField(label='Heading 2 Size (e.g. 32px)')
    h3FontSize = forms.CharField(label='Heading 3 Size (e.g. 24px)')

    # Jumbotron
    jumbotronPaddingV = forms.CharField(label='Hero Padding Top/Bottom (e.g. 50px)')
    jumbotronPaddingH = forms.CharField(label='Hero Padding Left/Right (e.g. 80px)')
    jumbotronFontSize = forms.CharField(label='Hero Text Size (e.g. 20px)')

    # Logo
    logoMarginRight = forms.CharField(label='Logo Right Margin (e.g. 80px)')
