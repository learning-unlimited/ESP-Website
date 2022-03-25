from django.contrib.auth.decorators import login_required, user_passes_test
from django.core import serializers
from django.http import HttpResponse
import json

""" Removed the staff-only restriction and instead pass a flag to ajax_autocomplete if the user
    is not a staff member.  The staff bit is checked at the per-function level, so that students
    can call ajax_autocomplete on K12School but not on User or DataTree (for example).

user_is_staff = user_passes_test(lambda u: u.is_authenticated() and u.is_staff and u.is_authenticated())
@user_is_staff
"""

def autocomplete_wrapper(function, data, is_staff, prog):
    if is_staff:
        if prog:
            return function(data, prog)
        return function(data)
    else:
        if 'allow_non_staff' in function.im_func.func_code.co_varnames:
            if prog:
                return function(data, prog)
            return function(data)
        else:
            return []

@login_required
def ajax_autocomplete(request):
    """
    This function will recieve a bunch of GET requests for the
    AjaxForeignKey, and return the data for the autocompletion.
    """
    try:
        limit = int(request.GET.get('limit',10))
        model_module = request.GET['model_module']
        model_name   = request.GET['model_name']
        ajax_func    = request.GET.get('ajax_func', 'ajax_autocomplete')
        data         = request.GET['ajax_data']
        prog         = request.GET['prog']
    except KeyError, ValueError:
        # bad request
        response = HttpResponse('Malformed Input')
        response.status_code = 400
        return response

    # import the model
    Model = getattr(__import__(model_module,(),(),[str(model_name)]),model_name)

    if hasattr(Model.objects, ajax_func):
        query_set = autocomplete_wrapper(getattr(Model.objects, ajax_func), data, request.user.is_staff, prog)
    else:
        query_set = autocomplete_wrapper(getattr(Model, ajax_func), data, request.user.is_staff, prog)

    output = list(query_set[:limit])
    output2 = []
    for item in output:
        output2.append({'id': item['id'], 'ajax_str': item['ajax_str']+' (%s)' % item['id']})

    content = json.dumps({'result':output2})

    return HttpResponse(content,
                        content_type = 'javascript/javascript')
