from django.contrib.auth.decorators import login_required, user_passes_test
from django.core import serializers
from django.http import HttpResponse
from django.utils import simplejson
from django.db.models.query import QuerySet

user_is_staff = user_passes_test(lambda u: u.is_authenticated() and u.is_staff and u.is_authenticated())

@user_is_staff
def ajax_autocomplete(request):
    """
    This function will recieve a bunch fo GET requests for the
    AjaxForeignKey, and return the data for the autocompletion.
    """
    try:
        limit = int(request.GET.get('limit',10))
        model_module = request.GET['model_module']
        model_name   = request.GET['model_name']
        ajax_func    = request.GET.get('ajax_func', 'ajax_autocomplete')
        data         = request.GET['ajax_data']
    except KeyError, ValueError:
        # bad request
        response = HttpResponse('Malformed Input')
        response.status_code = 400
        return response

    # import the model
    Model = getattr(__import__(model_module,(),(),['']),model_name)

    if hasattr(Model.objects, ajax_func):
        query_set = getattr(Model.objects, ajax_func)(data)
    else:
        query_set = getattr(Model, ajax_func)(data)

    if type(query_set) == QuerySet:
        raise NotImplementedError
    else:
        output = list(query_set[:limit])
        output2 = []
        for item in output:
            output2.append({'id': item['id'], 'ajax_str': item['ajax_str']+' (%s)' % item['id']})
        
        content = simplejson.dumps({'result':output2})

    return HttpResponse(content,
                        mimetype = 'javascript/javascript')
