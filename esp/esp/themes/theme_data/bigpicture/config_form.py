from django import forms

from esp.themes.forms import ThemeConfigurationForm
from esp.utils.widgets import NavStructureWidgetWithIcons

class ConfigForm(ThemeConfigurationForm):
    nav_structure = forms.Field(widget=NavStructureWidgetWithIcons)
