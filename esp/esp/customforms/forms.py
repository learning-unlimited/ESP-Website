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
        super().__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        """
        'value' is a OrderedDict
        """

        if value:
            return list(value.values())
        return [None, None]

    def format_output(self, rendered_widgets):
        html_string = '<table class="combo_field name_field">'
        html_string += '<tr><td class="small_field">' + rendered_widgets[0] + '</td><td class="small_field">' + rendered_widgets[1] + '</td></tr>'
        html_string += '<tr class="subtext_row"><td>' + 'First' + '</td><td>' + 'Last' + '</td></tr>'
        html_string += '</table>'
        return html_string

class HiddenNameWidget(NameWidget):
    """
    The hidden widget for the NameField class. Necessary to work with FormWizard
    """
    is_hidden = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for widget in self.widgets:
            widget.input_type = 'hidden'

    def format_output(self, rendered_widgets):
        return ''.join(rendered_widgets)

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
        super().__init__(fields, *args, **kwargs)

    def compress(self, value_list):
        compressed_value = OrderedDict()
        if value_list:
            compressed_value['%s_first_name' % self.name] = value_list[0]
            compressed_value['%s_last_name' % self.name] = value_list[1]
        return compressed_value

class AddressWidget(forms.MultiWidget):
    """
    Custom widget for the 'Address' compound field type.

    Sub-widget order (5 total):
      0 — street  (TextInput)
      1 — city    (TextInput)
      2 — state   (USStateSelect; "International" triggers postcode mode)
      3 — zip     (TextInput, US only — hidden when state == "International")
      4 — postcode (TextInput, international only — shown when state == "International")

    The zip/postcode toggle is handled by an inline <script> injected in
    format_output(). The script is self-contained (IIFE) so multiple
    AddressWidget instances on the same page don't interfere.

    Security: all values are sanitised by AddressField.compress() validators
    (validate_zip / validate_postcode). The widget itself performs no
    server-side input handling.
    """

    def __init__(self, wclass='', *args, **kwargs):
        widgets = (
            # 0: street
            forms.TextInput(attrs={'size': '70', 'class': wclass}),
            # 1: city
            forms.TextInput(attrs={'size': '30', 'class': wclass}),
            # 2: state dropdown — includes "International" option
            USStateSelect(attrs={'class': wclass}),
            # 3: US ZIP / ZIP+4 (hidden when International is selected)
            forms.TextInput(attrs={
                'size': '10',
                'class': wclass + ' cf-addr-zip',
                'placeholder': 'ZIP code',
                'aria-label': 'US ZIP code',
                'maxlength': '10',
            }),
            # 4: International postcode (hidden by default, shown for International)
            forms.TextInput(attrs={
                'size': '10',
                'class': wclass + ' cf-addr-postcode',
                'placeholder': 'Postcode',
                'aria-label': 'International postcode',
                'maxlength': '12',
                'style': 'display:none;',
            }),
        )
        super().__init__(widgets, *args, **kwargs)

    def decompress(self, value):
        """
        Split a stored OrderedDict back into individual widget values.

        Backward-compatible: old data produced by the 4-widget version only has
        4 values (no postcode). Pad to 5 so the new widget doesn't error.
        """
        if value:
            vals = list(value.values())
            # Pad with None for any missing sub-values (backward compat with 4-value data)
            while len(vals) < 5:
                vals.append(None)
            return vals[:5]
        return [None, None, None, None, None]

    def format_output(self, rendered_widgets):
        """
        Build the HTML table for the address widget and inject a small IIFE
        that toggles the ZIP / postcode row based on the state dropdown value.

        The script uses document.currentScript so it always references the
        table that immediately precedes it — safe with multiple address widgets
        on the same page and requires no global namespace pollution.
        """
        html_string = '<table class="combo_field address_field">'
        html_string += '<tr><td>Street&nbsp;' + rendered_widgets[0] + '</td></tr>'
        html_string += '<tr><td>City&nbsp;' + rendered_widgets[1] + '</td></tr>'
        html_string += '<tr><td>State&nbsp;' + rendered_widgets[2] + '</td></tr>'
        # ZIP row (US addresses) — toggled via JS
        html_string += (
            '<tr class="cf-zip-row"><td>'
            'ZIP&nbsp;&nbsp;' + rendered_widgets[3] +
            '</td></tr>'
        )
        # Postcode row (international) — hidden by default, toggled via JS
        html_string += (
            '<tr class="cf-postcode-row" style="display:none;"><td>'
            'Postcode&nbsp;' + rendered_widgets[4] +
            '</td></tr>'
        )
        html_string += '</table>'

        # Inline IIFE: toggle ZIP / postcode visibility based on state selection.
        # document.currentScript.previousElementSibling is the <table> above.
        # Security: only reads/writes element visibility and clears postcode on
        # US selection — no user data is written to innerHTML.
        html_string += (
            '<script>'
            '(function(){'
            'var s=document.currentScript;'
            'var tbl=s.previousElementSibling;'
            'var sel=tbl.querySelector("select");'
            'var zr=tbl.querySelector(".cf-zip-row");'
            'var pr=tbl.querySelector(".cf-postcode-row");'
            'var zi=tbl.querySelector(".cf-addr-zip");'
            'var pc=tbl.querySelector(".cf-addr-postcode");'
            'function upd(){'
            'var intl=sel.value==="International";'
            'zr.style.display=intl?"none":"";'
            'pr.style.display=intl?"":"none";'
            # When switching back to a US state, clear any stale postcode value
            # and re-enable the zip field so the server-side validator is satisfied.
            'if(!intl){pc.value="";}'
            # When switching to International, clear any stale zip value.
            'else{zi.value="";}'
            '}'
            'sel.addEventListener("change",upd);'
            'upd();'
            '})();'
            '</script>'
        )
        return html_string


class HiddenAddressWidget(AddressWidget):
    """
    The hidden widget for the AddressField class.
    Used by FormWizard to carry address data between steps without displaying it.
    All 5 sub-widgets are rendered as hidden inputs so both zip and postcode are
    preserved across wizard steps.
    """
    is_hidden = True

    def __init__(self, *args, **kwargs):
        super().__init__(wclass='', *args, **kwargs)
        # Replace all widgets with HiddenInput — 5 fields including postcode
        self.widgets = [
            forms.HiddenInput(),  # street
            forms.HiddenInput(),  # city
            forms.HiddenInput(),  # state
            forms.HiddenInput(),  # zip
            forms.HiddenInput(),  # postcode
        ]

    def format_output(self, rendered_widgets):
        return ''.join(rendered_widgets)


class AddressField(forms.MultiValueField):
    """
    Custom field for the 'Address' combo field type.

    Produces an OrderedDict with keys:
      {name}_street, {name}_city, {name}_state, {name}_zip, {name}_postcode

    Both zip and postcode are optional individually, but at least one must be
    provided when the form requires an address (enforced by the parent form's
    clean() method — e.g. UserContactForm.clean()).

    Security:
    - zip     max_length=10  supports US ZIP+4 ("12345-6789")
    - postcode max_length=12 supports all known international formats
    - USStateField rejects values not in the allowed state list
    """
    hidden_widget = HiddenAddressWidget

    def __init__(self, *args, **kwargs):
        if 'name' in kwargs:
            self.name = kwargs.pop('name')
        wclass = kwargs.pop('class')
        self.widget = AddressWidget(wclass=wclass)
        fields = (
            forms.CharField(max_length=100),   # street
            forms.CharField(max_length=50),    # city
            USStateField(),                    # state (includes International)
            forms.CharField(max_length=10, required=False),   # zip (US, optional)
            forms.CharField(max_length=12, required=False),   # postcode (intl, optional)
        )
        super().__init__(fields, require_all_fields=False, *args, **kwargs)

    def compress(self, value_list):
        """
        Pack the 5 sub-field values into an OrderedDict that maps to ContactInfo
        field names via DynamicForm._contactinfo_map.

        value_list indices:
          0 — street   → {name}_street
          1 — city     → {name}_city
          2 — state    → {name}_state
          3 — zip      → {name}_zip      (empty string → stored as '')
          4 — postcode → {name}_postcode (empty string → stored as '')
        """
        compressed_value = OrderedDict()
        if value_list:
            compressed_value['%s_street' % self.name] = value_list[0]
            compressed_value['%s_city' % self.name] = value_list[1]
            compressed_value['%s_state' % self.name] = value_list[2]
            # Guard against short value_list from old 4-widget data
            compressed_value['%s_zip' % self.name] = value_list[3] if len(value_list) > 3 else ''
            compressed_value['%s_postcode' % self.name] = value_list[4] if len(value_list) > 4 else ''
        return compressed_value
