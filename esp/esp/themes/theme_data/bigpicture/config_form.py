from django import forms

from esp.themes.forms import ThemeConfigurationForm
from esp.utils.widgets import NavStructureWidgetWithIcons

class ConfigForm(ThemeConfigurationForm):
    full_group_name = forms.CharField()
    nav_structure = forms.Field(widget=NavStructureWidgetWithIcons)
