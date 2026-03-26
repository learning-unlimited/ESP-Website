from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.http import HttpResponse
from django.http import HttpResponseForbidden
import json

_AUTOCOMPLETE_MODEL_ALLOWLIST = None

def _get_autocomplete_allowlist():
    global _AUTOCOMPLETE_MODEL_ALLOWLIST
    if _AUTOCOMPLETE_MODEL_ALLOWLIST is not None:
        return _AUTOCOMPLETE_MODEL_ALLOWLIST

    from esp.users.models import (
        ESPUser, K12School, ContactInfo,
        StudentInfo, TeacherInfo, GuardianInfo, EducatorInfo,
    )
    from esp.program.models.class_ import ClassSubject, ClassSection

    models = [
        ESPUser,
        K12School,
        ContactInfo,
        StudentInfo,
        TeacherInfo,
        GuardianInfo,
        EducatorInfo,
        ClassSubject,
        ClassSection,
    ]

    _AUTOCOMPLETE_MODEL_ALLOWLIST = {
        (model.__module__, model.__name__): model
        for model in models
    }

    return _AUTOCOMPLETE_MODEL_ALLOWLIST


def autocomplete_wrapper(function, data, is_staff, **kwargs):
    if is_staff:
        return function(data, **kwargs)
    else:
        if 'allow_non_staff' in function.__func__.__code__.co_varnames:
            return function(data, **kwargs)
        else:
            return []

@login_required
def ajax_autocomplete(request):
    """
    This function will receive a bunch of GET requests for the
    AjaxForeignKey, and return the data for the autocompletion.
    """
    try:
        limit = max(0, min(int(request.GET.get('limit', 10)), 50))
        model_module = request.GET['model_module']
        model_name   = request.GET['model_name']
        ajax_func    = request.GET.get('ajax_func', 'ajax_autocomplete')
        data         = request.GET['ajax_data']
        prog         = request.GET['prog']
        grade        = request.GET.get('grade')
        last_name_range = request.GET.get('last_name_range')
    except (KeyError, ValueError):
        response = HttpResponse('Malformed Input')
        response.status_code = 400
        return response

    # Resolve the model from the explicit allowlist — never via __import__.
    Model = _get_autocomplete_allowlist().get((model_module, model_name))
    if Model is None:
        return HttpResponseForbidden('Not allowed')

    from esp.program.models import Program
    try:
        prog_obj = Program.objects.get(id=prog)
    except (Program.DoesNotExist, ValueError):
        prog_obj = None

    kwargs = {'grade': grade, 'last_name_range': last_name_range, 'prog': prog_obj}

    if hasattr(Model.objects, ajax_func):
        query_set = autocomplete_wrapper(getattr(Model.objects, ajax_func), data, request.user.is_staff, **kwargs)
    else:
        query_set = autocomplete_wrapper(getattr(Model, ajax_func), data, request.user.is_staff, **kwargs)

    output = list(query_set[:limit])
    output2 = []
    for item in output:
        output2.append({'id': item['id'], 'ajax_str': f'{item["ajax_str"]} ({item["id"]})'})

    content = json.dumps({'result': output2})

    return HttpResponse(content, content_type='application/json')
