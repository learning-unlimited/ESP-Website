from django.http import HttpResponse
from django.template import Context, loader
from tmg.core.models import Project

# Create your views here.

def xml(request):
    """ Pull data from the database and dump it into the XML template for the video kiosk

    The video kiosk wants an XML-encoded list of all projects.  All encoding logic is handled by the template. """
    projects = Project.objects.all()
    t = loader.get_template('video_kiosk.xml')
    c = Context({
        'projects': projects,
        })
    return HttpResponse(t.render(c), mimetype='text/xml')
