from django.shortcuts import render_to_response
from django.template import RequestContext

def editor(request):
    return render_to_response('theme_editor/editor.html', {}, context_instance=RequestContext(request))

    
