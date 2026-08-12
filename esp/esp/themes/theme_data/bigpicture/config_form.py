from django import forms


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
    accent1 = forms.CharField(label='Primary Accent Color',required=False)
    accent2 = forms.CharField(label='Secondary Accent Color',required=False)
    navbarBackground = forms.CharField(label='Navbar Background',required=False)
    navbarText = forms.CharField(label='Navbar Text Color',required=False)
    navbarLinkColor = forms.CharField(label='Navbar Link Color',required=False)
    headingColor = forms.CharField(label='Heading Color',required=False)
    footerBackground = forms.CharField(label='Footer Background',required=False)
    footerText = forms.CharField(label='Footer Text Color',required=False)
    footerLinkColor = forms.CharField(label='Footer Link Color',required=False)
    linkColor = forms.CharField(label='Body Link Color',required=False)
    linkColorHover = forms.CharField(label='Body Link Hover Color',required=False)

    # Typography
    h1FontSize = forms.CharField(label='Heading 1 Size (e.g. 42px)',required=False)
    h2FontSize = forms.CharField(label='Heading 2 Size (e.g. 32px)',required=False)
    h3FontSize = forms.CharField(label='Heading 3 Size (e.g. 24px)',required=False)

    # Jumbotron
    jumbotronPaddingV = forms.CharField(label='Hero Padding Top/Bottom (e.g. 50px)',required=False)
    jumbotronPaddingH = forms.CharField(label='Hero Padding Left/Right (e.g. 80px)',required=False)
    jumbotronFontSize = forms.CharField(label='Hero Text Size (e.g. 20px)',required=False)

    # Logo
    logoMarginRight = forms.CharField(label='Logo Right Margin (e.g. 80px)',required=False)
