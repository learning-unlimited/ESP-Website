from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template import Context, Template
from esp.settings import PROJECT_ROOT
from django.http import HttpResponse, HttpResponseRedirect
from os import path
import re

# can we avoid hardcoding this?
less_dir = path.join(PROJECT_ROOT, 'public/media/theme_editor/less/') #directory containing modified less files
variables_template_less = path.join(less_dir, 'variables_template.less')
variables_less = path.join(less_dir, 'variables.less')

def parse_less(less_file):
    f = open(less_file).read()
    matches = re.findall("@(\w+):\s*([^,;]*)[,;]", f)
    d = {}
    for match in matches:
        d[match[0]] = match[1]
    return d
    
def editor(request):
    variables_settings = parse_less(variables_less)
#    return HttpResponse(str(variables_settings))
    return render_to_response('theme_editor/editor.html', variables_settings, context_instance=RequestContext(request))

def apply(request):
    variables_settings = parse_less(variables_less)
    f = open(variables_template_less)
    variables_template = Template(f.read())
    f.close()
    form_settings = dict(request.GET) # retrieve context from form input, change to POST eventually
    for k,v in form_settings.items():
        form_settings[k] = form_settings[k][0] # because QueryResponse objects store values as lists
        if not form_settings[k]: # if a form element returns no value, don't
            del form_settings[k];
    variables_settings.update(form_settings)
    w = variables_template.render(Context(variables_settings))
    f = open(variables_less, 'w')
    f.write(w)
    f.close()
    return HttpResponseRedirect('/theme/')
