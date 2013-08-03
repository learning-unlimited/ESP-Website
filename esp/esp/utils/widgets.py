#   Downloaded from http://www.djangosnippets.org/snippets/391/
#   Modified to not force unicode
#   - Michael P

from django.conf import settings
from django import forms
from django.forms import widgets
from django.utils.safestring import mark_safe
import django.utils.formats

import datetime
import time

from esp.utils import captcha

# DATETIMEWIDGET
calEnable = u"""
<script type="text/javascript">
    $j("#%s").%s({
        showOn: 'button',
        buttonImage: '%simages/calbutton_tight.png',
        buttonImageOnly: true,
        dateFormat: '%s',
        timeFormat: '%s'
    });
</script>"""

class DateTimeWidget(forms.widgets.TextInput):
    dformat = 'mm/dd/yy'
    tformat = 'hh:mm'
    pythondformat = '%m/%d/%Y %H:%M'

    # Note -- these are not actually used in the deadlines template, since we don't include
    # the entire form, just use variables from. They're here now mainly for responsibility
    class Media:
        css = {
            'all':  ('styles/jquery-ui/jquery-ui.css',)
        }
        js = ('scripts/jquery-ui.js',
              'scripts/jquery-ui.timepicker.js')
    
    def prepare_render_attrs(self, name, value, attrs=None):
        """ Base function for preparing information needed to render the widget. """

        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        
        if value != '': 
            try:
                final_attrs['value'] = value.strftime(self.pythondformat)
            except:
                final_attrs['value'] = value
                
        if not final_attrs.has_key('id'):
            final_attrs['id'] = u'%s_id' % (name)
        id = final_attrs['id']
        return final_attrs
        
    def render(self, name, value, attrs=None):
        final_attrs = self.prepare_render_attrs(name, value, attrs)
        id = final_attrs['id']
        cal = calEnable % (id, 'datetimepicker', settings.MEDIA_URL, self.dformat, self.tformat)
        return u'<input%s />%s' % (forms.util.flatatt(final_attrs), cal)

    def value_from_datadict(self, data, files, name):
        dtf = django.utils.formats.get_format('DATETIME_INPUT_FORMATS')
        empty_values = forms.fields.EMPTY_VALUES

        value = data.get(name, None)
        if value in empty_values:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        for format in dtf:
            try:
                return datetime.datetime(*(time.strptime(value, format)[:6]))
            except ValueError:
                continue
        return None
        
class DateWidget(DateTimeWidget):
    """ A stripped down version of the DateTimeWidget that uses jQuery UI's
        built in datepicker. """

    def render(self, name, value, attrs=None):
        final_attrs = self.prepare_render_attrs(name, value, attrs)
        id = final_attrs['id']
        cal = calEnable % (id, 'datepicker', settings.MEDIA_URL, self.dformat, self.tformat)
        return u'<input%s />%s' % (forms.util.flatatt(final_attrs), cal)
        
# TODO: Make this not suck
class SplitDateWidget(forms.MultiWidget):
    """ A date widget that separates days, etc. """

    def __init__(self, attrs=None, min_year=None, max_year=None):
        from datetime import datetime

        if min_year is None:
            min_year = datetime.now().year - 70
        if max_year is None:
            max_year = datetime.now().year - 10

        year_choices = range(min_year,
                             max_year+1)
        year_choices.reverse()
        month_choices = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        day_choices   = ['%02d' % x for x in range(1, 32)]
        choices = {'year' : [('',' ')] + zip(year_choices, year_choices),
                   'month': [('',' ')] + zip(range(1, 13), month_choices),
                   'day'  : [('',' ')] + zip(range(1, 32), day_choices)
                   }

        year_widget = forms.Select(choices=choices['year'])
        month_widget = forms.Select(choices=choices['month'])
        day_widget = forms.Select(choices=choices['day'])

        widgets = (month_widget, day_widget, year_widget)
        super(SplitDateWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        """ Splits datetime.date object into separate fields. """
        if value:
            return [value.month, value.day, value.year]
        return [None, None, None]

    def value_from_datadict(self, data, files, name):
        """ Given a dict, extracts datetime.date object. Appears to require handling of both versions. """
        from datetime import date
        val = data.get(name, None)
        if val is not None:
            return val
        else:
            vals = super(SplitDateWidget, self).value_from_datadict(data, files, name)
            try:
                return date(int(vals[2]), int(vals[0]), int(vals[1]))
            except:
                return None

    # Put labels in
    def format_output(self, rendered_widgets):
        output = u'\n<label for="dob_0">Month:</label>\n'
        output += rendered_widgets[0]
        output += u'\n<label for="dob_1">Day:</label>\n'
        output += rendered_widgets[1]
        output += u'\n<label for="dob_2">Year:</label>\n'
        output += rendered_widgets[2]
        return output

class CaptchaWidget(forms.widgets.TextInput):
    request = None
    
    def render(self, name, value, attrs=None):
        if self.request:
            return captcha.displayhtml(self.request, public_key=settings.RECAPTCHA_PUBLIC_KEY)
        else:
            raise ESPError(True), 'Captcha field initialized without request.  Please set the widget\'s request attribute.'
    
    def value_from_datadict(self, data, files, name):
        challenge = data.get('recaptcha_challenge_field')
        response = data.get('recaptcha_response_field')
        captcha_response = captcha.submit(challenge, response, settings.RECAPTCHA_PRIVATE_KEY, self.request.META['REMOTE_ADDR'])

        if captcha_response.is_valid:
            return True
        else:
            return None

class BlankSelectWidget(forms.Select):
    """ A <select> widget whose first entry is blank. """
    
    def __init__(self, blank_choice=('',''), *args, **kwargs):
        super(forms.Select, self).__init__(*args, **kwargs)
        self.blank_value = blank_choice[0]
        self.blank_label = blank_choice[1]
    
    # Copied from django/forms/widgets.py
    def render(self, name, value, attrs=None, choices=()):
        from django.utils.html import escape, conditional_escape
        from django.utils.encoding import force_unicode
        from django.utils.safestring import mark_safe
        
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<select%s>' % forms.util.flatatt(final_attrs)]
        output.append( u'<option value="%s" selected="selected">%s</option>' %
                       (escape(self.blank_value), conditional_escape(force_unicode(self.blank_label))) )
        options = self.render_options(choices, [value])
        if options:
            output.append(options)
        output.append('</select>')
        return mark_safe(u'\n'.join(output))
    

class NullRadioSelect(forms.RadioSelect):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = ((True, u'Yes'), (False, u'No'))
        super(NullRadioSelect, self).__init__(*args, **kwargs)


class NullCheckboxSelect(forms.CheckboxInput):
    def __init__(self, *args, **kwargs):
        super(NullCheckboxSelect, self).__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        """ Slightly modified from Django's version to accept "on" as True. """
        if name not in data:
            return False
        value = data.get(name)
        values =  {'on': True, 'true': True, 'false': False}
        if isinstance(value, basestring):
            value = values.get(value.lower(), value)
        print 'NullCheckboxSelect converted %s to %s' % (data.get(name), value)
        return value

class DummyWidget(widgets.Input):
    input_type = 'text'
    
    def value_from_datadict(self, data, files, name):
        return True
    
    def render(self, name, value, attrs=None, choices=()):
        output = u''
        if attrs and 'text' in attrs:
            output += attrs['text']
        return mark_safe(output)

