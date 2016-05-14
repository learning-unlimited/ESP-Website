from esp.users.models import ESPUser
from esp.varnish.varnish import purge_page
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied

def varnish_purge(request):
    # Authenticate
    if (not request.user or not request.user.is_authenticated() or not request.user.isAdministrator()):
        raise PermissionDenied
    # Purge the page specified
    purge_page(request.POST['page'])
    # Return the minimum possible
    return HttpResponse('')
