#   Downloaded from https://www.djangosnippets.org/snippets/391/
#   Modified to not force unicode
#   - Michael P

from django import forms
from django.conf import settings
from django.core.validators import EMPTY_VALUES
from django.forms import widgets
from django.template import Template, Context
from django.utils.safestring import mark_safe

import django.utils.formats
import datetime
import time
import json
import logging
import os
import re
logger = logging.getLogger(__name__)

class DateTimeWidget(forms.widgets.DateTimeInput):
    template_name = 'django/forms/widgets/datetimepicker.html'
    dformat = 'mm/dd/yy'
    tformat = 'hh:mm'
    pythondformat = '%m/%d/%Y %H:%M'
    jquerywidget = 'datetimepicker'

    # Note -- these are not actually used in the deadlines template, since we don't include
    # the entire form, just use variables from. They're here now mainly for responsibility
    class Media:
        css = {
            'all':  ('styles/jquery-ui/jquery-ui.css',)
        }
        js = ('scripts/jquery-ui.js',
              'scripts/jquery-ui.timepicker.js')

    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.format = self.pythondformat

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context.update({
            'id': attrs['id'] if 'id' in attrs else f'{name}_id',
            'jquerywidget': self.jquerywidget,
            'media_url': settings.MEDIA_URL,
            'date_format': self.dformat,
            'time_format': self.tformat,
        })
        return context

    def value_from_datadict(self, data, files, name):
        dtf = django.utils.formats.get_format('DATETIME_INPUT_FORMATS')
        empty_values = EMPTY_VALUES

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
    pythondformat = '%m/%d/%Y'
    jquerywidget = 'datepicker'

    def value_from_datadict(self, data, files, name):
        value = data.get(name, None)
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        for format in django.utils.formats.get_format('DATE_INPUT_FORMATS'):
            try:
                return datetime.date(*(time.strptime(value, format)[:3]))
            except ValueError:
                continue
        return None

class ClassAttrMergingSelect(forms.Select):

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = base_attrs.copy()
        #   Merge 'class' attributes - this is the difference from Django's default implementation
        if extra_attrs:
            if 'class' in attrs and 'class' in extra_attrs \
                    and isinstance(extra_attrs['class'], str):
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

        year_choices = list(range(min_year,
                             max_year+1))
        year_choices.reverse()
        month_choices = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        day_choices   = ['%02d' % x for x in range(1, 32)]
        choices = {'year' : [('', ' ')] + list(zip(year_choices, year_choices)),
                   'month': [('', ' ')] + list(zip(list(range(1, 13)), month_choices)),
                   'day'  : [('', ' ')] + list(zip(list(range(1, 32)), day_choices))
                   }

        year_widget = ClassAttrMergingSelect(choices=choices['year'], attrs={'class': 'input-small'})
        month_widget = ClassAttrMergingSelect(choices=choices['month'], attrs={'class': 'input-medium'})
        day_widget = ClassAttrMergingSelect(choices=choices['day'], attrs={'class': 'input-mini'})

        widgets = (month_widget, day_widget, year_widget)
        super().__init__(widgets, attrs)

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
            vals = super().value_from_datadict(data, files, name)
            try:
                return date(int(vals[2]), int(vals[0]), int(vals[1]))
            except (ValueError, TypeError, IndexError):
                return None

    #   Format output
    #   (labels are now aggregated at beginning of line, as if this is a single control)
    def format_output(self, rendered_widgets):
        return '\n'.join(rendered_widgets)

class BlankSelectWidget(forms.Select):
    """ A <select> widget whose first entry is blank. """
    template_name = 'django/forms/widgets/blankselect.html'

    def __init__(self, blank_choice=('', ''), *args, **kwargs):
        super(forms.Select, self).__init__(*args, **kwargs)
        self.blank_value = blank_choice[0]
        self.blank_label = blank_choice[1]

class NullRadioSelect(forms.RadioSelect):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = ((True, 'Yes'), (False, 'No'))
        super().__init__(*args, **kwargs)

class NullCheckboxSelect(forms.CheckboxInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        """ Slightly modified from Django's version to accept "on" as True. """
        if name not in data:
            return False
        value = data.get(name)
        values =  {'on': True, 'true': True, 'false': False}
        if isinstance(value, str):
            value = values.get(value.lower(), value)
        logger.info('NullCheckboxSelect converted %s to %s', data.get(name), value)
        return value

class DummyWidget(widgets.Input):
    input_type = 'text'

    def value_from_datadict(self, data, files, name):
        return True

    def render(self, name, value, attrs=None, choices=(), renderer=None):
        output = ''
        if attrs and 'text' in attrs:
            output += attrs['text']
        return mark_safe(output)

class ContactFieldsWidget(forms.Widget):
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
    {{ name }}_save();
}

function {{ name }}_add_link(obj, data)
{
    obj.append($j("<li />").addClass("ui-sortable-handle"));
    var entry = obj.children().last();
    %(add_link_body)s

    var delete_button = $j("<br/><button class='btn btn-mini btn-danger'>Delete link</button>");
    delete_button.on("click", {{ name }}_delete_link);
    entry.append(delete_button);
    $j("#{{ name }}_entries input").on("change", {{ name }}_save);
    {{ name }}_save()
}

function {{ name }}_save()
{
    var result = $j("#{{ name }}_entries").children("li").map(function (index, element) {
        return {
            icon: $j(element).children(".data_icon").val(),
            link: $j(element).children(".data_link").val(),
            text: $j(element).children(".data_text").val(),
        };
    }).get();
    $j("input[name={{ name }}]").val(JSON.stringify(result));
    return result;
}

function {{ name }}_setup()
{
    var {{ name }}_data = [];
    try {
        var raw_data = $j("#id_{{ name }}").val();
        if (raw_data) {
            {{ name }}_data = JSON.parse(raw_data);
        }
    } catch (e) {
        console.error("Failed to parse {{ name }} init data:", e);
    }
    var anchor_ul = $j("#{{ name }}_entries");
    for (var i = 0; i < {{ name }}_data.length; i++)
    {
        {{ name }}_add_link(anchor_ul, {{ name }}_data[i]);
    }
    var add_button = $j("<button class='btn btn-mini btn-primary'>Add link</button>");
    add_button.on("click", function (event) {
        event.preventDefault();
        {{ name }}_add_link(anchor_ul, {text: "contact us", link: "/contact.html", icon: ""});
    });
    anchor_ul.parent().append(add_button);
}

$j(document).ready(function() {
    {{ name }}_setup();
    $j("#{{ name }}_entries").sortable({
        update: function( event, ui ) {
            {{ name }}_save();
        }
    });
});
</script>
<style type="text/css">
#{{ name }}_entries {
    font-size: 0.9em;
}
#{{ name }}_entries input {
    font-size: 1.0em;
    margin-right: 5px;
}
#{{ name }}_entries .ui-sortable-handle {
    cursor: move;
    background: var(--bs-secondary-bg, lavender);
    color: var(--bs-emphasis-color, #333);
    padding: 5px;
    border-radius: 10px;
    border: dashed 1px lightgrey;
    margin-bottom: 5px;
}
</style>
"""

    # We separate out this part so subclasses can override it.
    add_link_body = """
        entry.append($j("<span>Text: </span>"));
        entry.append($j("<input class='data_text nav_secondary_field input-small' type='text' value='" + data.text + "' />"));
        entry.append($j("<br/><span>Link: </span>"));
        entry.append($j("<input class='data_link nav_secondary_field input-medium' type='text' value='" + data.link + "' />"));
    """

    def render(self, name, value, attrs=None, renderer=None):
        if value is None: value = ''
        self.build_attrs(attrs)
        context = {}
        context['name'] = name
        context['value'] = json.dumps(value)
        template = Template(self.template_text % {
            'add_link_body': self.add_link_body})
        return template.render(Context(context))

    def value_from_datadict(self, data, files, name):
        result = json.loads(data[name])
        return result

class NavStructureWidget(forms.Widget):
    # TODO(benkraft): Convert this to an actual static script so we don't have
    # to interpolate a pile of JS here.
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
    {{ name }}_save();
}

function {{ name }}_delete_tab(event)
{
    event.preventDefault();
    $j(this).parent().detach();
    {{ name }}_save();
}

function {{ name }}_add_link(obj, data)
{
    var entry_list = obj.children("ul");
    entry_list.append($j("<li />").addClass("ui-sortable-handle"));
    var entry = entry_list.children().last();
    %(add_link_body)s

    var delete_button = $j("<br/><button class='btn btn-mini btn-danger'>Delete link</button>");
    delete_button.on("click", {{ name }}_delete_link);
    entry.append(delete_button);
    $j("#{{ name }}_entries input, #{{ name }}_entries select").on("change", {{ name }}_save);
}

function {{ name }}_add_tab(obj, data)
{
    //  obj.children("li").last().after($j("<li />"));
    obj.append($j("<li />").addClass("ui-sortable-handle"));
    var category_li = obj.children("li").last();
    category_li.append($j("<span>Header text: </span>"));
    category_li.append($j("<input class='data_header nav_header_field input-small' type='text' value='" + data.header + "' />"));
    category_li.append($j("<br/><span>Header link: </span>"));
    category_li.append($j("<input class='data_header_link nav_header_field input-large' type='text' value='" + data.header_link + "' />"));

    category_li.append($j("<ul />"));
    var entry_list = category_li.children("ul");

    //  console.log("Links: ");
    for (var j = 0; j < data.links.length; j++)
    {
        {{ name }}_add_link(category_li, data.links[j]);
    }
    var add_button = $j("<button class='btn btn-mini'>Add link</button>");
    add_button.on("click", function (event) {
        event.preventDefault();
        {{ name }}_add_link($j(this).parent(), {text: "", link: "", icon: ""});
    });
    category_li.append(add_button);

    var delete_button = $j("<button class='btn btn-mini btn-danger' style='margin-left: 5px;'>Delete tab</button>");
    delete_button.on("click", {{ name }}_delete_tab);
    category_li.append(delete_button);
}

function {{ name }}_save()
{
    var result = $j("#{{ name }}_entries").children("li").map(function (index, element) {
        return {
            header: $j(element).children(".data_header").val(),
            header_link: $j(element).children(".data_header_link").val(),
            links: $j(element).children("ul").children("li").map(function (index, element) {
                return {
                    // note the first one may be undefined, which is fine.
                    icon: $j(element).children(".data_icon").val(),
                    link: $j(element).children(".data_link").val(),
                    text: $j(element).children(".data_text").val(),
                };
            }).get()
        };
    }).get();
    $j("input[name={{ name }}]").val(JSON.stringify(result));
    return result;
}

function {{ name }}_setup()
{
    var {{ name }}_data = [];
    try {
        var raw_data = $j("#id_{{ name }}").val();
        if (raw_data) {
            {{ name }}_data = JSON.parse(raw_data);
        }
    } catch (e) {
        console.error("Failed to parse {{ name }} init data:", e);
    }
    var anchor_ul = $j("#{{ name }}_entries");
    for (var i = 0; i < {{ name }}_data.length; i++)
    {
        {{ name }}_add_tab(anchor_ul, {{ name }}_data[i]);
    }
    var add_button = $j("<button class='btn btn-mini btn-primary'>Add tab</button>");
    add_button.on("click", function (event) {
        event.preventDefault();
        {{ name }}_add_tab(anchor_ul, {header: "", header_link: "", links: [{text: "", link: "", icon: ""}]});
    });
    anchor_ul.parent().append(add_button);

    anchor_ul.parents("form").submit({{ name }}_save);
}

$j(document).ready(function() {
    {{ name }}_setup();
    $j("#{{ name }}_entries").sortable({
        update: function( event, ui ) {
            {{ name }}_save();
        }
    });
    $j("#{{ name }}_entries ul").sortable({
        update: function( event, ui ) {
            {{ name }}_save();
        },
        connectWith: "#{{ name }}_entries ul"
    });
});
</script>
<style type="text/css">
#{{ name }}_entries {
    font-size: 0.9em;
}
#{{ name }}_entries input {
    font-size: 1.0em;
    margin-right: 5px;
}
#{{ name }}_entries .ui-sortable-handle {
    cursor: move;
    background: var(--bs-secondary-bg, beige);
    color: var(--bs-emphasis-color, #333);
    padding: 5px;
    border-radius: 10px;
    border: dashed 1px lightgrey;
    margin-bottom: 5px;
}
#{{ name }}_entries > .ui-sortable-handle {
    background: var(--bs-tertiary-bg, aliceblue);
}
</style>
"""

    # We separate out this part so subclasses can override it.
    add_link_body = """
        entry.append($j("<br/><span>Text: </span>"));
        entry.append($j("<input class='data_text nav_secondary_field input-small' type='text' value='" + data.text + "' />"));
        entry.append($j("<br/><span>Link: </span>"));
        entry.append($j("<input class='data_link nav_secondary_field input-large' type='text' value='" + data.link + "' />"));
    """

    def render(self, name, value, attrs=None, renderer=None):
        if value is None: value = ''
        self.build_attrs(attrs)
        context = {}
        context['name'] = name
        context['value'] = json.dumps(value)
        template = Template(self.template_text % {
            'add_link_body': self.add_link_body})
        return template.render(Context(context))

    def value_from_datadict(self, data, files, name):
        result = json.loads(data[name])
        return result

class WithOptionDataMixin(object):
    """ Mixin for choice widgets that renders extra ``data-`` attributes on each
        of the individual choice inputs.  ``option_data`` maps a choice value to
        a dict of attribute names (without the ``data-`` prefix) and values.  """

    def __init__(self, *args, **kwargs):
        #   Choice values are frequently model IDs, so normalize the keys to
        #   strings to avoid int/str mismatches at lookup time.
        self.option_data = {str(key): data for key, data in kwargs.pop('option_data', {}).items()}
        super().__init__(*args, **kwargs)

    #   create_option() is the hook shared by every rendering path
    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        for key, data in self.option_data.get(str(value), {}).items():
            option['attrs']['data-' + key] = data
        return option


class RadioSelectWithData(WithOptionDataMixin, forms.RadioSelect):
    pass


class CheckboxSelectMultipleWithData(WithOptionDataMixin, forms.CheckboxSelectMultiple):
    pass

class ChoiceWithOtherWidget(forms.MultiWidget):
    """MultiWidget for use with ChoiceWithOtherField."""
    template_name = 'django/forms/widgets/choicewithother.html'

    def __init__(self, choices, option_data):
        widgets = [
            RadioSelectWithData(choices=choices, option_data=option_data),
            forms.TextInput
        ]
        super().__init__(widgets)

    def decompress(self, value):
        if not value:
            return [None, None]
        return value

class ChoiceWithOtherField(forms.MultiValueField):
    def __init__(self, *args, **kwargs):
        option_data = kwargs.pop('option_data', {})
        fields = [
            forms.ChoiceField(widget=forms.RadioSelect(), *args, **kwargs),
            forms.CharField(required=False)
        ]

        self.choices = []

        if 'choices' in kwargs:
            self.choices = kwargs['choices']
            widget = ChoiceWithOtherWidget(choices=kwargs['choices'], option_data=option_data)
            kwargs.pop('choices')
            self._was_required = kwargs.pop('required', True)
            kwargs['required'] = False
            super().__init__(widget=widget, fields=fields, *args, **kwargs)
        else:
            super().__init__(*args, **kwargs)

    def compress(self, value):
        if not value:
            return [None, '']

        option_value, other_value = value
        if self._was_required and not value or option_value in (None, ''):
            raise forms.ValidationError(self.error_messages['required'])

        return option_value, other_value

def bootstrap_icons():
    """Return {name: codepoint} from the installed Bootstrap Icons package,
    which the themes render as <i class="bi bi-NAME">."""
    path = os.path.join(settings.MEDIA_ROOT, 'theme_editor', 'node_modules',
                        'bootstrap-icons', 'font', 'bootstrap-icons.json')
    try:
        with open(path) as f:
            icons = json.load(f)
    except (OSError, ValueError):
        logger.warning('Could not read the Bootstrap Icons list from %s', path)
        return {}
    return {name: codepoint for name, codepoint in icons.items()
            if re.fullmatch(r'[a-z0-9-]+', name) and isinstance(codepoint, int)}

class NavStructureWidgetWithIcons(NavStructureWidget):
    add_link_body = """
        entry.append($j("<span>Icon: </span>"));
        var select = $j("<select class='data_icon nav_secondary_field input-medium' />");
        select.css("font-family", "bootstrap-icons, var(--bs-body-font-family), sans-serif");
        select.html({{ name }}_icon_options());
        select.val(data.icon || "");
        if (data.icon && select.val() !== data.icon) {
            // Keep a saved name Bootstrap Icons lacks (e.g. an old Glyphicon) rather than dropping it on save
            select.append($j("<option />").val(data.icon).text(data.icon + " (not a Bootstrap Icons name)"));
            select.val(data.icon);
        }
        var preview = $j("<i class='bi ms-1' aria-hidden='true'></i>");
        var update_preview = function () {
            preview.attr("class", "bi ms-1" + (select.val() ? " bi-" + select.val() : ""));
        };
        select.on("change", update_preview);
        update_preview();
        entry.append(select).append(preview);
        %(super_add_link_body)s
    """ % {'super_add_link_body': NavStructureWidget.add_link_body}

    icon_script = """
<script type="text/javascript">
var %(name)s_icons = %(icons)s;
var %(name)s_icon_options_html = null;
function %(name)s_icon_options()
{
    if (%(name)s_icon_options_html === null) {
        %(name)s_icon_options_html = "<option value=''>(none)</option>" + %(name)s_icons.map(function (icon) {
            return "<option value='" + icon[0] + "'>" + String.fromCodePoint(icon[1]) + " " + icon[0] + "</option>";
        }).join("");
    }
    return %(name)s_icon_options_html;
}
</script>
"""

    def render(self, name, value, attrs=None, renderer=None):
        icons = json.dumps(sorted(bootstrap_icons().items()))
        script = self.icon_script % {'name': name, 'icons': icons}
        return mark_safe(script + super().render(name, value, attrs, renderer))
