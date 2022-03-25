from esp.program.models import ClassSubject
from esp.utils.web import render_to_response
from esp.tagdict.models import Tag
from django.db.models.query import Q
from django.http import HttpResponse
import json

# example value:
# { "bad_program_names": ["Delve", "SATPrep", "9001", "Test"],
#   "bad_titles": ["Lunch Period"] }
def good_random_class():
    constraints = json.loads(Tag.getTag('random_constraints'))
    q = Q()
    for bad_program_name in constraints.get('bad_program_names', []):
        q = q & ~Q(parent_program__name__icontains=bad_program_name)
    for bad_title in constraints.get('bad_titles', []):
        q = q & ~Q(title__iexact=bad_title)
    return ClassSubject.objects.random_class(q)

def main(request):
    return render_to_response("random/index.html", request,
        {'cls': good_random_class()})

def ajax(request):
    cls = good_random_class()
    data = {'title': cls.title,
            'program': cls.parent_program.niceName(),
            'info': cls.class_info,
            }
    return HttpResponse(json.dumps(data))
