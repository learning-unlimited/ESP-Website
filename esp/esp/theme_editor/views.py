from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template import Context, Template
from esp.settings import PROJECT_ROOT
from os import path

def editor(request):
    # can we avoid hardcoding this?
    less_dir = path.join(PROJECT_ROOT, 'public/media/theme_editor/less/') #directory containing modified less files
    variables_template_less = path.join(less_dir, 'variables_template.less')
    variables_less = path.join(less_dir, 'variables.less')
    f = open(variables_template_less)
    variables_template = Template(f.read())
    f.close()
    variables_context = {} # retrieve context from form input
    w = variables_template.render(Context(variables_context))
    f = open(variables_less, 'w')
    f.write(w)
    f.close()
    return render_to_response('theme_editor/editor.html', {}, context_instance=RequestContext(request))

    
