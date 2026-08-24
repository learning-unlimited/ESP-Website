from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
import inspect

""" Removed the staff-only restriction and instead pass a flag to ajax_autocomplete if the user
    is not a staff member.  The staff bit is checked at the per-function level, so that students
    can call ajax_autocomplete on K12School but not on User or DataTree (for example).

user_is_staff = user_passes_test(lambda u: u.is_authenticated and u.is_staff and u.is_authenticated)
@user_is_staff
"""

def autocomplete_wrapper(function, data, is_staff, **kwargs):
    """Call the model's ajax_autocomplete; pass request if the function accepts it."""
    # Both checks below read the callee's declared parameters.  inspect.signature is
    # used rather than __code__.co_varnames because co_varnames also lists local
    # variables (so a local named 'allow_non_staff' would read as an opt-in) and it
    # describes the outermost function, so a decorated ajax_autocomplete reports the
    # decorator's (*args, **kwargs) instead of the parameters it actually forwards.
    try:
        sig = inspect.signature(function)
    except (TypeError, ValueError):
        # Some C-implemented callables have no introspectable signature.  Treat them
        # as accepting nothing rather than guessing.
        params = {}
    else:
        params = sig.parameters

    # Only pass 'request' if the function actually accepts it
    if 'request' not in params:
        kwargs.pop('request', None)

    if is_staff:
        return function(data, **kwargs)

    # Non-staff callers only get through to autocompletes that opt in by declaring an
    # explicit 'allow_non_staff' parameter.  A bare **kwargs is deliberately *not* an
    # opt-in: accepting arbitrary keywords says nothing about whether the data is safe
    # to expose, and several staff-only autocompletes take **kwargs
    # (e.g. ESPUser.ajax_autocomplete_student).
    if 'allow_non_staff' in params:
        return function(data, **kwargs)
    return []

@login_required
def ajax_autocomplete(request):
    """
    This function will receive a bunch of GET requests for the
    AjaxForeignKey, and return the data for the autocompletion.
    """
    try:
        limit = int(request.GET.get('limit', 10))
        model_module = request.GET['model_module']
        model_name   = request.GET['model_name']
        ajax_func    = request.GET.get('ajax_func', 'ajax_autocomplete')
        data         = request.GET['ajax_data']
        prog         = request.GET['prog']
        grade        = request.GET.get('grade')
        last_name_range = request.GET.get('last_name_range')
    except (KeyError, ValueError):
        # bad request
        return JsonResponse({'error': 'Malformed Input'}, status=400)


    # import the model
    try:
        Model = getattr(__import__(model_module, (), (), [str(model_name)]), model_name)
    except AttributeError:
        return JsonResponse({'error': 'Malformed Input'}, status=400)

    from esp.program.models import Program
    try:
        prog_obj = Program.objects.get(id=prog)
    except (Program.DoesNotExist, ValueError):
        prog_obj = None

    kwargs = {'grade': grade, 'last_name_range': last_name_range, 'prog': prog_obj, 'request': request}

    func = getattr(Model.objects, ajax_func) if hasattr(Model.objects, ajax_func) else getattr(Model, ajax_func)
    query_set = autocomplete_wrapper(func, data, request.user.is_staff, **kwargs)

    output = list(query_set[:limit])
    output2 = []
    for item in output:
        output2.append({'id': item['id'], 'ajax_str': f'{item["ajax_str"]} ({item["id"]})'})

    return JsonResponse({'result': output2})
