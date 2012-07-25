from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template import Context, Template
from esp.settings import PROJECT_ROOT
from django.http import HttpResponse, HttpResponseRedirect
from esp.users.models import admin_required
import subprocess
from os import path, remove
import re
import shutil
import glob

# can we avoid hardcoding this?
less_dir = path.join(PROJECT_ROOT, 'public/media/theme_editor/less/') #directory containing less files used by theme editor
themes_dir = path.join(PROJECT_ROOT, 'public/media/theme_editor/themes/') #directory containing the themes
variables_template_less = path.join(less_dir, 'variables_template.less')
variables_less = path.join(less_dir, 'variables.less')
# directory containing the javascript that shows the palette
palette_dir = path.join(PROJECT_ROOT, 'public/media/theme_editor/')

# and this...
sans_serif_fonts = {"Impact":"Impact, Charcoal, sans-serif",
                    "Palatino Linotype":"'Palatino Linotype', 'Book Antiqua', Palatino, serif",
                    "Tahoma":"Tahoma, Geneva, sans-serif",
                    "Century Gothic":"'Century Gothic', sans-serif",
                    "Lucida Sans Unicode":"'Lucida Sans Unicode', 'Lucida Grande', sans-serif",
                    "Arial Black":"'Arial Black', Gadget, sans-serif",
                    "Times New Roman":"'Times New Roman', Times, serif",
                    "Arial Narrow":"'Arial Narrow', sans-serif",
                    "Verdana":"Verdana, Geneva, sans-serif",
                    "Copperplate Gothic Light":"'Copperplate Gothic Light', Copperplate, sans-serif",
                    "Lucida Console":"'Lucida Console', Monaco, monospace",
                    "Gill Sans":"'Gill Sans', 'Gill Sans MT', sans-serif",
                    "Trebuchet MS":"'Trebuchet MS', Helvetica', sans-serif",
                    "Courier New":"'Courier New', Courier, monospace",
                    "Arial":"Arial, Helvetica, sans-serif",
                    "Georgia":"Georgia, serif"}

def get_theme_name(theme_file_path):
    f = open(theme_file_path).read()
    return re.search(r"// Theme Name: (.+?)\n", f).group(1)


def parse_less(less_file_path):
    try:
        f = open(less_file_path).read()
    #this regex is supposed to match @(property) = (value);
    #or @(property) = (function)(args) in match[0] and 
    #match[1] respectively
        matches = re.findall(r"@(\w+):\s*([^,;\(]*)[,;\(]", f)
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
        match = re.findall(r"palette:([\#]?\w+);", f) 
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
    
    f = open(variables_template_less)
    variables_template = Template(f.read())
    f.close()
    form_settings = dict(request.POST) # retrieve context from form input, change to POST eventually

    for k,v in form_settings.items():
        if len(form_settings[k]) == 1:
            form_settings[k] = form_settings[k][0] # because QueryResponse objects store values as lists
        if not form_settings[k]: # if a form element returns no value, don't keep it in the context
            del form_settings[k];

    variables_settings.update(form_settings)

    # if theme is only applied, but has some changes, just apply theme and set name as 'None'
    if 'apply' in request.POST:
        del variables_settings['theme_name']

    w = variables_template.render(Context(variables_settings))
    f = open(theme_file_path, 'w')
    f.write(w)
    f.close()

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
    if 'save' in request.POST:
        if request.POST['saveThemeName'] == '':
            theme_name = get_theme_name(variables_less)
            if theme_name == 'None':
                return HttpResponseRedirect('/theme/')
        else:
            theme_name = request.POST['saveThemeName']
        save_file_name = theme_name + '.less'
        save(request, save_file_name)
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
        save(request, 'variables.less')
    elif 'reset' in request.POST:
        pass
    else: 
        return HttpResponseRedirect('/')
    f = open(path.join(themes_dir, 'bootstrap.css'), 'w')
    # finally compile less to css
    subprocess.call(["lessc", "--compress", path.join(less_dir, 'bootstrap.less')], stdout=f, shell=True)
    f.close()
    # for debugging, uncomment the next line
    #return HttpResponse(str(dict(request.POST)))


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

    return render_to_response('theme_editor/editor.html', context, context_instance=RequestContext(request))

