#   Downloaded from http://www.djangosnippets.org/snippets/391/
#   Modified to not force unicode
#   - Michael P

from __future__ import absolute_import
from django import forms
from django.conf import settings
from django.forms import widgets
from django.template import Template, Context
from django.utils.safestring import mark_safe

from collections import OrderedDict

import django.utils.formats
import datetime
import time
import json
import logging
import six
from six.moves import range
from six.moves import zip
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
            'id': attrs['id'] if 'id' in attrs else six.u('%s_id') % (name),
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
                    and (isinstance(extra_attrs['class'], str) or isinstance(extra_attrs['class'], six.text_type)):
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

    def __init__(self, blank_choice=('', ''), *args, **kwargs):
        super(forms.Select, self).__init__(*args, **kwargs)
        self.blank_value = blank_choice[0]
        self.blank_label = blank_choice[1]

class NullRadioSelect(forms.RadioSelect):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = ((True, six.u('Yes')), (False, six.u('No')))
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
        if isinstance(value, str) or isinstance(value, six.text_type):
            value = values.get(value.lower(), value)
        logger.info('NullCheckboxSelect converted %s to %s', data.get(name), value)
        return value

class DummyWidget(widgets.Input):
    input_type = 'text'

    def value_from_datadict(self, data, files, name):
        return True

    def render(self, name, value, attrs=None, choices=()):
        output = six.u('')
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

    var delete_button = $j("<button class='btn btn-mini btn-danger'>Delete link</button>");
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
    var {{ name }}_data = JSON.parse($j("#id_{{ name }}").val());
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
    background: lavender;
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

    var delete_button = $j("<button class='btn btn-mini btn-danger'>Delete link</button>");
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
    category_li.append($j("<input class='data_header nav_header_field input-mini' type='text' value='" + data.header + "' />"));
    category_li.append($j("<span>Header link: </span>"));
    category_li.append($j("<input class='data_header_link nav_header_field' type='text' value='" + data.header_link + "' />"));

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
    var {{ name }}_data = JSON.parse($j("#id_{{ name }}").val());
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
    background: beige;
    padding: 5px;
    border-radius: 10px;
    border: dashed 1px lightgrey;
    margin-bottom: 5px;
}
#{{ name }}_entries > .ui-sortable-handle {
    background: aliceblue;
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

class RadioSelectWithData(forms.RadioSelect):
    def __init__(self, *args, **kwargs):
        self.option_data = kwargs.pop('option_data', {})
        super(RadioSelectWithData, self).__init__(*args, **kwargs)

    # https://stackoverflow.com/a/59274893/4660582
    def get_context(self, name, value, attrs):
        context = super(RadioSelectWithData, self).get_context(name, value, attrs)
        for optgroup in context['widget'].get('optgroups', []):
            for option in optgroup[1]:
                for k, v in six.iteritems(self.option_data.get(option['value'], {})):
                    option['attrs']['data-' + k] = v
        return context

class ChoiceWithOtherWidget(forms.MultiWidget):
    """MultiWidget for use with ChoiceWithOtherField."""
    template_name = 'django/forms/widgets/choicewithother.html'

    def __init__(self, choices, option_data):
        widgets = [
            RadioSelectWithData(choices=choices, option_data=option_data),
            forms.TextInput
        ]
        super(ChoiceWithOtherWidget, self).__init__(widgets)

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
            super(ChoiceWithOtherField, self).__init__(widget=widget, fields=fields, *args, **kwargs)
        else:
            super(ChoiceWithOtherField, self).__init__(*args, **kwargs)


    def compress(self, value):
        if not value:
            return [None, six.u('')]

        option_value, other_value = value
        if self._was_required and not value or option_value in (None, ''):
            raise forms.ValidationError(self.error_messages['required'])

        return option_value, other_value

# copied from esp/public/media/theme_editor/less/glyphicons.less
# TODO(benkraft): avoid the duplication
_ICONS = OrderedDict([
    ("asterisk", "&#x002a"),
    ("plus", "&#x002b"),
    ("euro", "&#x20ac"),
    ("minus", "&#x2212"),
    ("cloud", "&#x2601"),
    ("envelope", "&#x2709"),
    ("pencil", "&#x270f"),
    ("glass", "&#xe001"),
    ("music", "&#xe002"),
    ("search", "&#xe003"),
    ("heart", "&#xe005"),
    ("star", "&#xe006"),
    ("star-empty", "&#xe007"),
    ("user", "&#xe008"),
    ("film", "&#xe009"),
    ("th-large", "&#xe010"),
    ("th", "&#xe011"),
    ("th-list", "&#xe012"),
    ("ok", "&#xe013"),
    ("remove", "&#xe014"),
    ("zoom-in", "&#xe015"),
    ("zoom-out", "&#xe016"),
    ("off", "&#xe017"),
    ("signal", "&#xe018"),
    ("cog", "&#xe019"),
    ("trash", "&#xe020"),
    ("home", "&#xe021"),
    ("file", "&#xe022"),
    ("time", "&#xe023"),
    ("road", "&#xe024"),
    ("download-alt", "&#xe025"),
    ("download", "&#xe026"),
    ("upload", "&#xe027"),
    ("inbox", "&#xe028"),
    ("play-circle", "&#xe029"),
    ("repeat", "&#xe030"),
    ("refresh", "&#xe031"),
    ("list-alt", "&#xe032"),
    ("lock", "&#xe033"),
    ("flag", "&#xe034"),
    ("headphones", "&#xe035"),
    ("volume-off", "&#xe036"),
    ("volume-down", "&#xe037"),
    ("volume-up", "&#xe038"),
    ("qrcode", "&#xe039"),
    ("barcode", "&#xe040"),
    ("tag", "&#xe041"),
    ("tags", "&#xe042"),
    ("book", "&#xe043"),
    ("bookmark", "&#xe044"),
    ("print", "&#xe045"),
    ("camera", "&#xe046"),
    ("font", "&#xe047"),
    ("bold", "&#xe048"),
    ("italic", "&#xe049"),
    ("text-height", "&#xe050"),
    ("text-width", "&#xe051"),
    ("align-left", "&#xe052"),
    ("align-center", "&#xe053"),
    ("align-right", "&#xe054"),
    ("align-justify", "&#xe055"),
    ("list", "&#xe056"),
    ("indent-left", "&#xe057"),
    ("indent-right", "&#xe058"),
    ("facetime-video", "&#xe059"),
    ("picture", "&#xe060"),
    ("map-marker", "&#xe062"),
    ("adjust", "&#xe063"),
    ("tint", "&#xe064"),
    ("edit", "&#xe065"),
    ("share", "&#xe066"),
    ("check", "&#xe067"),
    ("move", "&#xe068"),
    ("step-backward", "&#xe069"),
    ("fast-backward", "&#xe070"),
    ("backward", "&#xe071"),
    ("play", "&#xe072"),
    ("pause", "&#xe073"),
    ("stop", "&#xe074"),
    ("forward", "&#xe075"),
    ("fast-forward", "&#xe076"),
    ("step-forward", "&#xe077"),
    ("eject", "&#xe078"),
    ("chevron-left", "&#xe079"),
    ("chevron-right", "&#xe080"),
    ("plus-sign", "&#xe081"),
    ("minus-sign", "&#xe082"),
    ("remove-sign", "&#xe083"),
    ("ok-sign", "&#xe084"),
    ("question-sign", "&#xe085"),
    ("info-sign", "&#xe086"),
    ("screenshot", "&#xe087"),
    ("remove-circle", "&#xe088"),
    ("ok-circle", "&#xe089"),
    ("ban-circle", "&#xe090"),
    ("arrow-left", "&#xe091"),
    ("arrow-right", "&#xe092"),
    ("arrow-up", "&#xe093"),
    ("arrow-down", "&#xe094"),
    ("share-alt", "&#xe095"),
    ("resize-full", "&#xe096"),
    ("resize-small", "&#xe097"),
    ("exclamation-sign", "&#xe101"),
    ("gift", "&#xe102"),
    ("leaf", "&#xe103"),
    ("fire", "&#xe104"),
    ("eye-open", "&#xe105"),
    ("eye-close", "&#xe106"),
    ("warning-sign", "&#xe107"),
    ("plane", "&#xe108"),
    ("calendar", "&#xe109"),
    ("random", "&#xe110"),
    ("comment", "&#xe111"),
    ("magnet", "&#xe112"),
    ("chevron-up", "&#xe113"),
    ("chevron-down", "&#xe114"),
    ("retweet", "&#xe115"),
    ("shopping-cart", "&#xe116"),
    ("folder-close", "&#xe117"),
    ("folder-open", "&#xe118"),
    ("resize-vertical", "&#xe119"),
    ("resize-horizontal", "&#xe120"),
    ("hdd", "&#xe121"),
    ("bullhorn", "&#xe122"),
    ("bell", "&#xe123"),
    ("certificate", "&#xe124"),
    ("thumbs-up", "&#xe125"),
    ("thumbs-down", "&#xe126"),
    ("hand-right", "&#xe127"),
    ("hand-left", "&#xe128"),
    ("hand-up", "&#xe129"),
    ("hand-down", "&#xe130"),
    ("circle-arrow-right", "&#xe131"),
    ("circle-arrow-left", "&#xe132"),
    ("circle-arrow-up", "&#xe133"),
    ("circle-arrow-down", "&#xe134"),
    ("globe", "&#xe135"),
    ("wrench", "&#xe136"),
    ("tasks", "&#xe137"),
    ("filter", "&#xe138"),
    ("briefcase", "&#xe139"),
    ("fullscreen", "&#xe140"),
    ("dashboard", "&#xe141"),
    ("paperclip", "&#xe142"),
    ("heart-empty", "&#xe143"),
    ("link", "&#xe144"),
    ("phone", "&#xe145"),
    ("pushpin", "&#xe146"),
    ("usd", "&#xe148"),
    ("gbp", "&#xe149"),
    ("sort", "&#xe150"),
    ("sort-by-alphabet", "&#xe151"),
    ("sort-by-alphabet-alt", "&#xe152"),
    ("sort-by-order", "&#xe153"),
    ("sort-by-order-alt", "&#xe154"),
    ("sort-by-attributes", "&#xe155"),
    ("sort-by-attributes-alt", "&#xe156"),
    ("unchecked", "&#xe157"),
    ("expand", "&#xe158"),
    ("collapse-down", "&#xe159"),
    ("collapse-up", "&#xe160"),
    ("log-in", "&#xe161"),
    ("flash", "&#xe162"),
    ("log-out", "&#xe163"),
    ("new-window", "&#xe164"),
    ("record", "&#xe165"),
    ("save", "&#xe166"),
    ("open", "&#xe167"),
    ("saved", "&#xe168"),
    ("import", "&#xe169"),
    ("export", "&#xe170"),
    ("send", "&#xe171"),
    ("floppy-disk", "&#xe172"),
    ("floppy-saved", "&#xe173"),
    ("floppy-remove", "&#xe174"),
    ("floppy-save", "&#xe175"),
    ("floppy-open", "&#xe176"),
    ("credit-card", "&#xe177"),
    ("transfer", "&#xe178"),
    ("cutlery", "&#xe179"),
    ("header", "&#xe180"),
    ("compressed", "&#xe181"),
    ("earphone", "&#xe182"),
    ("phone-alt", "&#xe183"),
    ("tower", "&#xe184"),
    ("stats", "&#xe185"),
    ("sd-video", "&#xe186"),
    ("hd-video", "&#xe187"),
    ("subtitles", "&#xe188"),
    ("sound-stereo", "&#xe189"),
    ("sound-dolby", "&#xe190"),
    ("sound-5-1", "&#xe191"),
    ("sound-6-1", "&#xe192"),
    ("sound-7-1", "&#xe193"),
    ("copyright-mark", "&#xe194"),
    ("registration-mark", "&#xe195"),
    ("cloud-download", "&#xe197"),
    ("cloud-upload", "&#xe198"),
    ("tree-conifer", "&#xe199"),
    ("tree-deciduous", "&#xe200"),
    ("cd", "&#xe201"),
    ("save-file", "&#xe202"),
    ("open-file", "&#xe203"),
    ("level-up", "&#xe204"),
    ("copy", "&#xe205"),
    ("paste", "&#xe206"),
    ("alert", "&#xe209"),
    ("equalizer", "&#xe210"),
    ("king", "&#xe211"),
    ("queen", "&#xe212"),
    ("pawn", "&#xe213"),
    ("bishop", "&#xe214"),
    ("knight", "&#xe215"),
    ("baby-formula", "&#xe216"),
    ("tent", "&#x26fa"),
    ("blackboard", "&#xe218"),
    ("bed", "&#xe219"),
    ("apple", "&#xf8ff"),
    ("erase", "&#xe221"),
    ("hourglass", "&#x231b"),
    ("lamp", "&#xe223"),
    ("duplicate", "&#xe224"),
    ("piggy-bank", "&#xe225"),
    ("scissors", "&#xe226"),
    ("bitcoin", "&#xe227"),
    ("btc", "&#xe227"),
    ("xbt", "&#xe227"),
    ("yen", "&#x00a5"),
    ("jpy", "&#x00a5"),
    ("ruble", "&#x20bd"),
    ("rub", "&#x20bd"),
    ("scale", "&#xe230"),
    ("ice-lolly", "&#xe231"),
    ("ice-lolly-tasted", "&#xe232"),
    ("education", "&#xe233"),
    ("option-horizontal", "&#xe234"),
    ("option-vertical", "&#xe235"),
    ("menu-hamburger", "&#xe236"),
    ("modal-window", "&#xe237"),
    ("oil", "&#xe238"),
    ("grain", "&#xe239"),
    ("sunglasses", "&#xe240"),
    ("text-size", "&#xe241"),
    ("text-color", "&#xe242"),
    ("text-background", "&#xe243"),
    ("object-align-top", "&#xe244"),
    ("object-align-bottom", "&#xe245"),
    ("object-align-horizontal", "&#xe246"),
    ("object-align-left", "&#xe247"),
    ("object-align-vertical", "&#xe248"),
    ("object-align-right", "&#xe249"),
    ("triangle-right", "&#xe250"),
    ("triangle-left", "&#xe251"),
    ("triangle-bottom", "&#xe252"),
    ("triangle-top", "&#xe253"),
    ("console", "&#xe254"),
    ("superscript", "&#xe255"),
    ("subscript", "&#xe256"),
    ("menu-left", "&#xe257"),
    ("menu-right", "&#xe258"),
    ("menu-down", "&#xe259"),
    ("menu-up", "&#xe260"),
])

class NavStructureWidgetWithIcons(NavStructureWidget):
    add_link_body = """
        entry.append($j("<span>Icon: </span>"));
        var select = $j("<select style='font-family: Glyphicons Halflings'" +
                        "class='data_icon nav_secondary_field input-medium glyphicon' />");
        select.append($j("<option style='font-family: Glyphicons Halflings' value=''" +
                         (data.icon ? "" : " selected") +
                         ">(none)</option>"));
        %(entries)s
        entry.append(select);
        %(super_add_link_body)s
    """ % {
        'super_add_link_body': NavStructureWidget.add_link_body,
        'entries': '\n'.join('''
            select.append($j("<option style='font-family: Glyphicons Halflings' value='%(icon)s'" +
                             (data.icon === "%(icon)s" ? " selected" : "") +
                             ">%(unicode)s (%(icon)s)</option>"));'''
            % {'icon': icon, 'unicode': text_unicode}
            for icon, text_unicode in _ICONS.items()),
    }
