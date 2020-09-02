#   Downloaded from http://www.djangosnippets.org/snippets/391/
#   Modified to not force unicode
#   - Michael P

from django import forms
from django.conf import settings
from django.forms import widgets
from django.template import Template, Context
from django.utils.safestring import mark_safe

import django.utils.formats
import datetime
import time
import json
import logging
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
        super(DateTimeWidget, self).__init__(attrs)
        self.format = self.pythondformat

    def get_context(self, name, value, attrs):
        context = super(DateTimeWidget, self).get_context(name, value, attrs)
        context.update({
            'id': attrs['id'] if 'id' in attrs else u'%s_id' % (name),
            'jquerywidget': self.jquerywidget,
            'media_url': settings.MEDIA_URL,
            'date_format': self.dformat,
            'time_format': self.tformat,
        })
        return context

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
    pythondformat = '%m/%d/%Y'
    jquerywidget = 'datepicker'

class ClassAttrMergingSelect(forms.Select):

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = base_attrs.copy()
        #   Merge 'class' attributes - this is the difference from Django's default implementation
        if extra_attrs:
            if 'class' in attrs and 'class' in extra_attrs \
                    and (isinstance(extra_attrs['class'], str) or isinstance(extra_attrs['class'], unicode)):
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


class BlankSelectWidget(forms.Select):
    """ A <select> widget whose first entry is blank. """
    template_name = 'django/forms/widgets/blankselect.html'

    def __init__(self, blank_choice=('',''), *args, **kwargs):
        super(forms.Select, self).__init__(*args, **kwargs)
        self.blank_value = blank_choice[0]
        self.blank_label = blank_choice[1]

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
        if isinstance(value, str) or isinstance(value, unicode):
            value = values.get(value.lower(), value)
        logger.info('NullCheckboxSelect converted %s to %s', data.get(name), value)
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
    %(add_link_body)s

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
        {{ name }}_add_link(category_li, data.links[j]);
    }
    var add_button = $j("<button class='btn btn-mini'>Add link</button>");
    add_button.click(function (event) {
        event.preventDefault();
        {{ name }}_add_link($j(this).parent(), {text: "", link: "", icon: ""});
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
    var {{ name }}_data = JSON.parse($j("#id_{{ name }}").val());
    var anchor_ul = $j("#{{ name }}_entries");
    for (var i = 0; i < {{ name }}_data.length; i++)
    {
        {{ name }}_add_tab(anchor_ul, {{ name }}_data[i]);
    }
    var add_button = $j("<button class='btn btn-mini btn-primary'>Add tab</button>");
    add_button.click(function (event) {
        event.preventDefault();
        {{ name }}_add_tab(anchor_ul, {header: "", header_link: "", links: [{text: "", link: "", icon: ""}]});
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

    # We separate out this part so subclasses can override it.
    add_link_body = """
        entry.append($j("<span>Text: </span>"));
        entry.append($j("<input class='data_text nav_secondary_field input-small' type='text' value='" + data.text + "' />"));
        entry.append($j("<span>Link: </span>"));
        entry.append($j("<input class='data_link nav_secondary_field' type='text' value='" + data.link + "' />"));
    """

    def render(self, name, value, attrs=None):
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

class ChoiceWithOtherWidget(forms.MultiWidget):
    """MultiWidget for use with ChoiceWithOtherField."""
    template_name = 'django/forms/widgets/choicewithother.html'

    def __init__(self, choices):
        widgets = [
            forms.RadioSelect(choices=choices),
            forms.TextInput
        ]
        super(ChoiceWithOtherWidget, self).__init__(widgets)

    def decompress(self, value):
        if not value:
            return [None, None]
        return value

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

        return option_value, other_value

# copied from esp/public/media/theme_editor/less/glyphicons.less
# TODO(benkraft): avoid the duplication
_ICONS = [
    "asterisk",
    "plus",
    "euro",
    "minus",
    "cloud",
    "envelope",
    "pencil",
    "glass",
    "music",
    "search",
    "heart",
    "star",
    "star-empty",
    "user",
    "film",
    "th-large",
    "th",
    "th-list",
    "ok",
    "remove",
    "zoom-in",
    "zoom-out",
    "off",
    "signal",
    "cog",
    "trash",
    "home",
    "file",
    "time",
    "road",
    "download-alt",
    "download",
    "upload",
    "inbox",
    "play-circle",
    "repeat",
    "refresh",
    "list-alt",
    "lock",
    "flag",
    "headphones",
    "volume-off",
    "volume-down",
    "volume-up",
    "qrcode",
    "barcode",
    "tag",
    "tags",
    "book",
    "bookmark",
    "print",
    "camera",
    "font",
    "bold",
    "italic",
    "text-height",
    "text-width",
    "align-left",
    "align-center",
    "align-right",
    "align-justify",
    "list",
    "indent-left",
    "indent-right",
    "facetime-video",
    "picture",
    "map-marker",
    "adjust",
    "tint",
    "edit",
    "share",
    "check",
    "move",
    "step-backward",
    "fast-backward",
    "backward",
    "play",
    "pause",
    "stop",
    "forward",
    "fast-forward",
    "step-forward",
    "eject",
    "chevron-left",
    "chevron-right",
    "plus-sign",
    "minus-sign",
    "remove-sign",
    "ok-sign",
    "question-sign",
    "info-sign",
    "screenshot",
    "remove-circle",
    "ok-circle",
    "ban-circle",
    "arrow-left",
    "arrow-right",
    "arrow-up",
    "arrow-down",
    "share-alt",
    "resize-full",
    "resize-small",
    "exclamation-sign",
    "gift",
    "leaf",
    "fire",
    "eye-open",
    "eye-close",
    "warning-sign",
    "plane",
    "calendar",
    "random",
    "comment",
    "magnet",
    "chevron-up",
    "chevron-down",
    "retweet",
    "shopping-cart",
    "folder-close",
    "folder-open",
    "resize-vertical",
    "resize-horizontal",
    "hdd",
    "bullhorn",
    "bell",
    "certificate",
    "thumbs-up",
    "thumbs-down",
    "hand-right",
    "hand-left",
    "hand-up",
    "hand-down",
    "circle-arrow-right",
    "circle-arrow-left",
    "circle-arrow-up",
    "circle-arrow-down",
    "globe",
    "wrench",
    "tasks",
    "filter",
    "briefcase",
    "fullscreen",
    "dashboard",
    "paperclip",
    "heart-empty",
    "link",
    "phone",
    "pushpin",
    "usd",
    "gbp",
    "sort",
    "sort-by-alphabet",
    "sort-by-alphabet-alt",
    "sort-by-order",
    "sort-by-order-alt",
    "sort-by-attributes",
    "sort-by-attributes-alt",
    "unchecked",
    "expand",
    "collapse-down",
    "collapse-up",
    "log-in",
    "flash",
    "log-out",
    "new-window",
    "record",
    "save",
    "open",
    "saved",
    "import",
    "export",
    "send",
    "floppy-disk",
    "floppy-saved",
    "floppy-remove",
    "floppy-save",
    "floppy-open",
    "credit-card",
    "transfer",
    "cutlery",
    "header",
    "compressed",
    "earphone",
    "phone-alt",
    "tower",
    "stats",
    "sd-video",
    "hd-video",
    "subtitles",
    "sound-stereo",
    "sound-dolby",
    "sound-5-1",
    "sound-6-1",
    "sound-7-1",
    "copyright-mark",
    "registration-mark",
    "cloud-download",
    "cloud-upload",
    "tree-conifer",
    "tree-deciduous",
    "cd",
    "save-file",
    "open-file",
    "level-up",
    "copy",
    "paste",
    "alert",
    "equalizer",
    "king",
    "queen",
    "pawn",
    "bishop",
    "knight",
    "baby-formula",
    "tent",
    "blackboard",
    "bed",
    "apple",
    "erase",
    "hourglass",
    "lamp",
    "duplicate",
    "piggy-bank",
    "scissors",
    "bitcoin",
    "btc",
    "xbt",
    "yen",
    "jpy",
    "ruble",
    "rub",
    "scale",
    "ice-lolly",
    "ice-lolly-tasted",
    "education",
    "option-horizontal",
    "option-vertical",
    "menu-hamburger",
    "modal-window",
    "oil",
    "grain",
    "sunglasses",
    "text-size",
    "text-color",
    "text-background",
    "object-align-top",
    "object-align-bottom",
    "object-align-horizontal",
    "object-align-left",
    "object-align-vertical",
    "object-align-right",
    "triangle-right",
    "triangle-left",
    "triangle-bottom",
    "triangle-top",
    "console",
    "superscript",
    "subscript",
    "menu-left",
    "menu-right",
    "menu-down",
    "menu-up",
]

class NavStructureWidgetWithIcons(NavStructureWidget):
    # TODO(benkraft): Add some way of seeing the icons while selecting them.
    add_link_body = """
        entry.append($j("<span>Icon: </span>"));
        var select = $j("<select class='data_icon nav_secondary_field input-small' />");
        select.append($j("<option value=''" +
                         (data.icon ? "" : " selected") +
                         ">(none)</option>"));
        %(entries)s
        entry.append(select);
        %(super_add_link_body)s
    """ % {
        'super_add_link_body': NavStructureWidget.add_link_body,
        'entries': '\n'.join('''
            select.append($j("<option value='%(icon)s'" +
                             (data.icon === "%(icon)s" ? " selected" : "") +
                             ">glyphicon-%(icon)s</option>"));'''
            % {'icon': icon}
            for icon in _ICONS),
    }
