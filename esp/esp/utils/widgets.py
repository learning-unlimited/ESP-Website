#   Downloaded from http://www.djangosnippets.org/snippets/391/
#   Modified to not force unicode
#   - Michael P
import datetime
import simplejson as json
import time

from django import forms
from django.conf import settings
from django.contrib.localflavor.us.forms import *
from django.forms import widgets
from django.template import Template, Context
from django.utils.encoding import StrAndUnicode, force_unicode
from django.utils.safestring import mark_safe
from django.utils.safestring import mark_safe
import django.utils.formats


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
        
class ClassAttrMergingSelect(forms.Select):

    def build_attrs(self, extra_attrs=None, **kwargs):
        attrs = dict(self.attrs, **kwargs)
        #   Merge 'class' attributes - this is the difference from Django's default implementation
        if extra_attrs:
            if 'class' in attrs and 'class' in extra_attrs \
                    and isinstance(extra_attrs['class'], basestring):
                attrs['class'] += ' ' + extra_attrs['class']
                del extra_attrs['class']
            attrs.update(extra_attrs)
        return attrs

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

        year_widget = ClassAttrMergingSelect(choices=choices['year'], attrs={'class': 'input-small'})
        month_widget = ClassAttrMergingSelect(choices=choices['month'], attrs={'class': 'input-medium'})
        day_widget = ClassAttrMergingSelect(choices=choices['day'], attrs={'class': 'input-mini'})
        
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

    #   Format output
    #   (labels are now aggregated at beginning of line, as if this is a single control)
    def format_output(self, rendered_widgets):
        return '\n'.join(rendered_widgets)

class CaptchaWidget(forms.widgets.TextInput):
    request = None
    
    def render(self, name, value, attrs=None):
        if self.request:
            return captcha.displayhtml(self.request, public_key=settings.RECAPTCHA_PUBLIC_KEY)
        else:
            raise ESPError('Captcha field initialized without request.  Please set the widget\'s request attribute.', log=True)
    
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

class NavStructureWidget(forms.Widget):
    template_text = """
<input type="hidden" id="id_{{ name }}" name="{{ name }}" value="{{ value }}" />
<div id="{{ name }}_options">
<ul id="{{ name }}_entries"></ul>
</div>
<script type="text/javascript">
function {{ name }}_delete_link(event)
{
    event.preventDefault();
    $j(this).parent().detach();
}

function {{ name }}_delete_tab(event)
{
    event.preventDefault();
    $j(this).parent().detach();
}

function {{ name }}_add_link(obj, data)
{
    var entry_list = obj.children("ul");
    entry_list.append($j("<li />"));
    var entry = entry_list.children().last();
    entry.append($j("<span>Text: </span>"));
    entry.append($j("<input class='data_text nav_secondary_field input-small' type='text' value='" + data.text + "' />"));
    entry.append($j("<span>Link: </span>"));
    entry.append($j("<input class='data_link nav_secondary_field' type='text' value='" + data.link + "' />"));
    
    var delete_button = $j("<button class='btn btn-mini btn-danger'>Delete link</button>");
    delete_button.click({{ name }}_delete_link);
    entry.append(delete_button);
}

function {{ name }}_add_tab(obj, data)
{
    //  obj.children("li").last().after($j("<li />"));
    obj.append($j("<li />"));
    var category_li = obj.children("li").last();
    category_li.append($j("<span>Header text: </span>"));
    category_li.append($j("<input class='data_header nav_header_field input-mini' type='text' value='" + data.header + "' />"));
    category_li.append($j("<span>Header link: </span>"));
    category_li.append($j("<input class='data_header_link nav_header_field' type='text' value='" + data.header_link + "' />"));
    var delete_button = $j("<button class='btn btn-mini btn-danger'>Delete tab</button>");
    delete_button.click({{ name }}_delete_tab);
    category_li.append(delete_button);
    
    category_li.append($j("<ul />"));
    var entry_list = category_li.children("ul");
    
    //  console.log("Links: ");
    for (var j = 0; j < data.links.length; j++)
    {
        {{ name }}_add_link(category_li, {text: data.links[j].text, link: data.links[j].link})
    }
    var add_button = $j("<button class='btn btn-mini'>Add link</button>");
    add_button.click(function (event) {
        event.preventDefault();
        {{ name }}_add_link($j(this).parent(), {text: "", link: ""});
    });
    category_li.append(add_button);
}

function {{ name }}_save()
{
    var result = $j("#{{ name }}_entries").children("li").map(function (index, element) {
        return {
            header: $j(element).children(".data_header").val(),
            header_link: $j(element).children(".data_header_link").val(),
            links: $j(element).children("ul").children("li").map(function (index, element) {
                return {
                    link: $j(element).children(".data_link").val(),
                    text: $j(element).children(".data_text").val()
                };
            }).get()
        };
    }).get();
    $j("input[name={{ name }}]").val(JSON.stringify(result));
    return result;
}

function {{ name }}_setup()
{
    var {{ name }}_data = JSON.parse($j("#id_{{ name }}").val());
    var anchor_ul = $j("#{{ name }}_entries");
    for (var i = 0; i < {{ name }}_data.length; i++)
    {
        {{ name }}_add_tab(anchor_ul, {{ name }}_data[i]);
    }
    var add_button = $j("<button class='btn btn-mini btn-primary'>Add tab</button>");
    add_button.click(function (event) {
        event.preventDefault();
        {{ name }}_add_tab(anchor_ul, {header: "", header_link: "", links: [{text: "", link: ""}]});
    });
    anchor_ul.parent().append(add_button);
    
    anchor_ul.parents("form").submit({{ name }}_save);
}

$j(document).ready({{ name }}_setup);
</script>
<style type="text/css">
#{{ name }}_entries {
    font-size: 0.9em;
}
#{{ name }}_entries input {
    font-size: 1.0em;
    margin-right: 5px;
}
</style>
"""

    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        context = {}
        context['name'] = name
        context['value'] = json.dumps(value)
        template = Template(NavStructureWidget.template_text)
        return template.render(Context(context))

    def value_from_datadict(self, data, files, name):
        result = json.loads(data[name])
        return result
        
#adapted from https://djangosnippets.org/snippets/863/
class ChoiceWithOtherRenderer(forms.RadioSelect.renderer):
    """RadioFieldRenderer that renders its last choice with a placeholder."""
    def __init__(self, *args, **kwargs):
        super(ChoiceWithOtherRenderer, self).__init__(*args, **kwargs)
        self.choices, self.other = self.choices[:-1], self.choices[-1]

    def __iter__(self):
        for input in super(ChoiceWithOtherRenderer, self).__iter__():
            yield input
        id = '%s_%s' % (self.attrs['id'], self.other[0]) if 'id' in self.attrs else ''
        label_for = ' for="%s"' % id if id else ''
        checked = '' if not force_unicode(self.other[0]) == self.value else 'checked="true" '
        yield '<label%s><input type="radio" id="%s" value="%s" name="%s" %s/> %s</label> %%s' % (
            label_for, id, self.other[0], self.name, checked, self.other[1])


class ChoiceWithOtherWidget(forms.MultiWidget):
    """MultiWidget for use with ChoiceWithOtherField."""
    def __init__(self, choices):
        widgets = [
            forms.RadioSelect(choices=choices, renderer=ChoiceWithOtherRenderer),
            forms.TextInput
        ]
        super(ChoiceWithOtherWidget, self).__init__(widgets)

    def decompress(self, value):
        if not value:
            return [None, None]
        return value

    def format_output(self, rendered_widgets):
        """Format the output by substituting the "other" choice into the first widget."""
        return rendered_widgets[0] % rendered_widgets[1]


class ChoiceWithOtherField(forms.MultiValueField):
    def __init__(self, *args, **kwargs):
        fields = [
            forms.ChoiceField(widget=forms.RadioSelect(), *args, **kwargs),
            forms.CharField(required=False)
        ]

        self.choices = []

        if 'choices' in kwargs:
            self.choices = kwargs['choices']
            widget = ChoiceWithOtherWidget(choices=kwargs['choices'])
            kwargs.pop('choices')
            self._was_required = kwargs.pop('required', True)
            kwargs['required'] = False
            super(ChoiceWithOtherField, self).__init__(widget=widget, fields=fields, *args, **kwargs)
        else:
             super(ChoiceWithOtherField, self).__init__(*args,**kwargs)


    def compress(self, value):
        if not value:
            return [None, u'']

        option_value, other_value = value

        if self._was_required and not value or option_value in (None, ''):
            raise forms.ValidationError(self.error_messages['required'])

        #if custom choice is selected
        custom_value = self.choices[-1][0]
        is_custom = option_value == custom_value 
        if is_custom and not other_value:#this would be the value of the last choice
            raise forms.ValidationError(self.error_messages['required'])
        else:
            return option_value, option_value
        
        return other_value, option_value

