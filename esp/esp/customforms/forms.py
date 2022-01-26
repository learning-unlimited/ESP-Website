from django.forms.fields import Select
from django import forms
from collections import OrderedDict
from localflavor.us.forms import USStateField, USStateSelect
from django.utils.html import conditional_escape

class CustomFileWidget(forms.ClearableFileInput):
    """
    Custom widget for the 'File' field to fix the URL.
    """
    def get_template_substitution_values(self, value):
        """
        Return value-related substitutions.
        """
        return {
            'initial': conditional_escape(value.url.split("/")[-1]),
            'initial_url': conditional_escape("/" + value.url.split("/public/")[1])
        }

class NameWidget(forms.MultiWidget):
    """
    Custom widget for the 'Name' field
    """
    def __init__(self, wclass='', *args, **kwargs):
        widgets =(forms.TextInput(attrs={'class': wclass}), forms.TextInput(attrs={'class': wclass}))
        super(NameWidget, self).__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        """
        'value' is a OrderedDict
        """

        if value:
            return value.values()
        return [None, None]

    def format_output(self, rendered_widgets):
        html_string = u'<table class="combo_field name_field">'
        html_string += u'<tr><td class="small_field">' + rendered_widgets[0] + u'</td><td class="small_field">' + rendered_widgets[1] + u'</td></tr>'
        html_string += u'<tr class="subtext_row"><td>' + u'First' + u'</td><td>' + u'Last' + u'</td></tr>'
        html_string += u'</table>'
        return html_string

class HiddenNameWidget(NameWidget):
    """
    The hidden widget for the NameField class. Necessary to work with FormWizard
    """
    is_hidden = True

    def __init__(self, *args, **kwargs):
        super(HiddenNameWidget, self).__init__(*args, **kwargs)
        for widget in self.widgets:
            widget.input_type = 'hidden'

    def format_output(self, rendered_widgets):
        return u''.join(rendered_widgets)

class NameField(forms.MultiValueField):
    """
    Custom field for the 'Name' field
    """
    hidden_widget = HiddenNameWidget

    def __init__(self, *args, **kwargs):
        if 'name' in kwargs:
            self.name = kwargs.pop('name')
        widget_class = kwargs.pop('class')
        self.widget = NameWidget(wclass=widget_class)
        fields = (forms.CharField(), forms.CharField())
        super(NameField, self).__init__(fields, *args, **kwargs)

    def compress(self, value_list):
        compressed_value = OrderedDict()
        if value_list:
            compressed_value['%s_first_name' % self.name] = value_list[0]
            compressed_value['%s_last_name' % self.name] = value_list[1]
        return compressed_value

class AddressWidget(forms.MultiWidget):
    """
    Custom widget for the 'Address' compound field type
    """
    def __init__(self, wclass='', *args, **kwargs):
        widgets = (
                    forms.TextInput(attrs={'size': '70', 'class': wclass}),
                    forms.TextInput(attrs={'size': '30', 'class': wclass}),
                    USStateSelect(attrs={'class': wclass}),
                    forms.TextInput(attrs={'size': '5', 'class': wclass + ' USZip'})
                )
        super(AddressWidget, self).__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        if value:
            return value.values()
        return [None, None, None, None]

    def format_output(self, rendered_widgets):
        html_string = u'<table class="combo_field address_field">'
        html_string += u'<tr><td>Street&nbsp;' + rendered_widgets[0] + '</td></tr>'
        html_string += u'<tr><td>City&nbsp;' + rendered_widgets[1] + u'</td></tr><tr><td>State&nbsp;' + rendered_widgets[2] + u'</td></tr>'
        html_string += u'<tr><td>Zip&nbsp;&nbsp;' + rendered_widgets[3] + u'</td></tr>'
        html_string += u'</table>'
        return html_string

class HiddenAddressWidget(AddressWidget):
    """
    The hidden widget for the AddressField class
    """
    is_hidden = True

    def __init__(self, *args, **kwargs):
        super(HiddenAddressWidget, self).__init__(wclass='', *args, **kwargs)
        self.widgets = [forms.HiddenInput(), forms.HiddenInput(), forms.HiddenInput(), forms.HiddenInput()]

    def format_output(self, rendered_widgets):
        return u''.join(rendered_widgets)

class AddressField(forms.MultiValueField):
    """
    Custom field for the 'Address' combo field type
    """
    hidden_widget = HiddenAddressWidget

    def __init__(self, *args, **kwargs):
        if 'name' in kwargs:
            self.name = kwargs.pop('name')
        wclass = kwargs.pop('class')
        self.widget = AddressWidget(wclass=wclass)
        fields = (forms.CharField(max_length=100), forms.CharField(max_length=50), USStateField(), forms.CharField(max_length=5))
        super(AddressField, self).__init__(fields, *args, **kwargs)

    def compress(self, value_list):
        compressed_value = OrderedDict()
        if value_list:
            compressed_value['%s_street' % self.name] = value_list[0]
            compressed_value['%s_city' % self.name] = value_list[1]
            compressed_value['%s_state' % self.name] = value_list[2]
            compressed_value['%s_zip' % self.name] = value_list[3]
        return compressed_value
