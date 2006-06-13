from django.http import HttpResponse
from django.template import Context, loader
from tmg.core.models import Project

# Create your views here.

def xml(request):
    projects = Project.objects.all()
    t = loader.get_template('video_kiosk.xml')
    c = Context({
        'projects': projects,
        })
    return HttpResponse(t.render(c), mimetype='text/xml')
