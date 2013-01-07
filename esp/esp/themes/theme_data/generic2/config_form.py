
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""


from esp.themes.forms import ThemeConfigurationForm
from esp.program.models import Program
from django import forms
from django.template import Template, Context

import simplejson as json

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
        print 'Value from datadict: %s' % result
        return result

class ConfigForm(ThemeConfigurationForm):
    title_text = forms.CharField()
    subtitle_text = forms.CharField()
    titlebar_prefix = forms.CharField()
    featured_programs = forms.ModelMultipleChoiceField(queryset=Program.objects.all())
    nav_structure = forms.Field(widget=NavStructureWidget)

    def prepare_for_serialization(self, data):
        result = data.copy()

        #   Replace "featured programs" with list of (url, name) dicts
        result['featured_programs'] = [{'name': prog.niceName(), 'url': prog.getUrlBase()} for prog in data['featured_programs']]

        return result

    def recover_from_serialization(self, data):
        result = data.copy()

        #   Replace "featured programs" (url, name) dicts with actual programs
        result['featured_programs'] = [Program.objects.get(anchor__uri__icontains=x['url']) for x in data['featured_programs']]

        return result
