
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template import Context, Template
from django.http import HttpResponse, HttpResponseRedirect

from esp.users.models import admin_required
from esp.themes.settings import *
from esp.themes.controllers import ThemeController

import subprocess
from os import path, remove
import re
import shutil
import glob

def get_theme_name(theme_file_path):
    f = open(theme_file_path).read()
    return re.search(r"// Theme Name: (.+?)\n", f).group(1)


def parse_less(less_file_path):
    try:
        f = open(less_file_path).read()
    #this regex is supposed to match @(property) = (value);
    #or @(property) = (function)(args) in match[0] and 
    #match[1] respectively
        matches = re.findall("@(\w+):\s*(.*?);", f)
        d = {}
        for match in matches:
            d[match[0]] = match[1]
        #in case color values like @white, @black are encountered, substitute
        #that with the hex value
            if match[1] and match[1][1:] in d and d[match[1][1:]][0] == '#':
                d[match[0]] = d[match[1][1:]]
        #if theme_name is set, retrieve that
        match = re.search(r"// Theme Name: (.+?)\n", f)
        if match:
            d.update({'theme_name':match.group(1)})
        # retrieve the palette
        match = re.findall(r"palette:(#?\w+?);", f) 
        palette = []
        for m in match:
            palette.append(m)
        d.update({'palette':palette})
        return d
    except IOError:
        return {}

def save(request, less_file):
    
    # when only applying, you want to write the changes to variables.less, and otherwise to the relevant theme file
    if 'apply' in request.POST:
        theme_file_path = path.join(less_dir, less_file) #less_file should always be 'variables.less' in this case?
    else:
        theme_file_path = path.join(themes_dir, less_file)

    variables_settings = parse_less(theme_file_path)

    # when the theme is saved for the first time, less_file doesn't exist, so parse_less will return an empty dict
    if not variables_settings or 'theme_name' not in variables_settings or variables_settings['theme_name'] == 'None':
        variables_settings['theme_name'] = less_file[:-5]

        # if theme is saved without a name, just set it as default with the name 'None'
        if variables_settings['theme_name'] == '': 
            del variables_settings['theme_name']
    
    form_settings = dict(request.POST) # retrieve context from form input, change to POST eventually

    for k,v in form_settings.items():
        if len(form_settings[k]) == 1:
            form_settings[k] = form_settings[k][0] # because QueryResponse objects store values as lists
        if not form_settings[k]: # if a form element returns no value, don't keep it in the context
            del form_settings[k];

    # if only one palette colour is defined, make sure it is one element in a list, so for example
    # Django doesn't split up 'black' into 'b','l',...,'k'.
    if 'palette' in form_settings and form_settings['palette'].__class__ != list:
        form_settings['palette'] = [form_settings['palette']]

    variables_settings.update(form_settings)

    # if theme is only applied, but has some changes, just apply theme and set name as 'None'
    if 'apply' in request.POST:
        del variables_settings['theme_name']
    f = open(theme_file_path, 'w')
    f.write(render_to_string('themes/bootstrap_variables.less', Context(variables_settings)))
    f.close()
    
    return variables_settings

def apply_theme(less_file):
    # in case you are trying to restore the last used settings
    if less_file == 'variables_backup.less': 
        temp_file = path.join(less_dir, 'variables_backup_temp.less')
        try:
            shutil.copy(path.join(less_dir,less_file),temp_file)
            shutil.copy(variables_less, path.join(less_dir, less_file))
            shutil.copy(temp_file, variables_less)
            remove(temp_file)
        except shutil.Error:
            pass
        return

    less_file = path.join(themes_dir, less_file)
    try:
        shutil.copy(variables_less, path.join(less_dir, 'variables_backup.less'))
        shutil.copy(less_file, variables_less)
    except shutil.Error:
        pass

def delete_theme(theme_name):
    remove(path.join(themes_dir, theme_name))
    if get_theme_name(variables_less) == theme_name:
        apply_theme('Default.less')

def generate_default():
    f = open(variables_template_less)
    variables_template = Template(f.read())
    f.close()
    w = variables_template.render(Context({'theme_name':'Default'}))
    f = open(path.join(themes_dir, 'Default.less'), 'w')
    f.write(w)
    f.close()

def update_palette(palette_list):
    # is it worth making a new file just for this?
    palette_template = 'var palette_list = [{% for color in palette %} "{{color}}"{% if not forloop.last %},{% endif %} {% endfor %}];'
    template = Template(palette_template)
    w = template.render(Context({'palette':palette_list}))
    f = open(path.join(palette_dir, 'palette.js'), 'w')
    f.write(w)
    f.close()

@admin_required
def theme_submit(request):
    variables_settings = None
    if 'save' in request.POST:
        if request.POST['saveThemeName'] == '':
            theme_name = get_theme_name(variables_less)
            if theme_name == 'None':
                return HttpResponseRedirect('/theme/')
        else:
            theme_name = request.POST['saveThemeName']
        save_file_name = theme_name + '.less'
        variables_settings = save(request, save_file_name)
        apply_theme(save_file_name)
    elif 'load' in request.POST:
        if request.POST['loadThemeName'] == 'Default':
            generate_default()
            apply_theme('Default.less')
        else:
            apply_theme(request.POST['loadThemeName']+'.less')
    elif 'delete' in request.POST:
        remove(path.join(themes_dir, request.POST['loadThemeName']+'.less'))
    elif 'apply' in request.POST:
        shutil.copy(variables_less, path.join(less_dir,'variables_backup.less'))
        variables_settings = save(request, 'variables.less')
    elif 'reset' in request.POST:
        pass
    else: 
        return HttpResponseRedirect('/')
    
    #   Re-generate the CSS for the current theme given the supplied settings
    if variables_settings:
        tc = ThemeController()
        tc.customize_theme('generic1', variables_settings)
    
    return HttpResponseRedirect('/theme/')

@admin_required    
def editor(request):
    context = parse_less(path.join(less_dir, variables_less))
    # load a list of available themes
    available_themes_paths = glob.glob(path.join(themes_dir,'*.less'))
    available_themes = []
    for theme_path in available_themes_paths:
        search_results = re.search(r'theme_editor/themes/(.+)\.less',theme_path)
        if search_results:
            available_themes.append(search_results.group(1))
    context.update({'available_themes':available_themes})
    context.update({'last_used_settings':'variables_backup'})
    # load a bunch of preset fonts
    context.update({'sans_fonts':sorted(sans_serif_fonts.iteritems())})
    # load the theme's palette
    update_palette(context['palette'])
#    for debugging, see context by uncommenting the next line
#    return HttpResponse(str(context))

    return render_to_response('themes/editor.html', context, context_instance=RequestContext(request))

def layout(request):
    return render_to_response('main-html/mockup.html', {}, context_instance=RequestContext(request))
