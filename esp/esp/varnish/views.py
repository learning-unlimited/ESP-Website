from esp.users.models import ESPUser
from esp.varnish.varnish import purge_page
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST

@require_POST
def varnish_purge(request):
    # Authenticate
    if (not request.user or not request.user.is_authenticated or not request.user.isAdministrator()):
        raise PermissionDenied
    # Purge the page specified
    page = request.POST.get('page')
    if not page:
        return HttpResponseBadRequest('')
    purge_page(page)
    # Return the minimum possible
    return HttpResponse('')
