from esp.users.models import ESPUser
from esp.varnish import purge_page
from django.http import HttpResponse

def varnish_purge(request):
    # Authenticate
    if (not request.user or not request.user.is_authenticated() or not ESPUser(request.user).isAdministrator()):
        raise PermissionDenied
    # Purge the page specified
    purge_page(request.POST['page'])
    # Return the minimum possible
    return HttpResponse('')
