from esp.program.models import ClassSubject
from esp.utils.web import render_to_response
from django.http import HttpResponse
import json

def main(request):
    return render_to_response("random/index.html", request,
        {'cls': ClassSubject.objects.random_class()})

def ajax(request):
    cls = ClassSubject.objects.random_class()
    data = {'title': cls.title,
            'program': cls.parent_program.niceName(),
            'info': cls.class_info,
            }
    return HttpResponse(json.dumps(data))
