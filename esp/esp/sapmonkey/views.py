from apiclient.discovery import build
from oauth2client.client import OAuth2Credentials
import httplib2

from django.conf import settings
from django.http import HttpResponse, Http404

from esp.users.models import admin_required, ESPUser

OAUTH_SCOPE = "https://www.googleapis.com/auth/drive"

@admin_required
def check_auth(request):
    return HttpResponse("SAPmonkey connected!")

@admin_required
def lookup_username(request, username):
    result = ESPUser.objects.filter(username=username)
    if (len(result) != 1):
        raise Http404
    
    user = result[0]
    if (user.email.strip().endswith("@mit.edu")):
        return HttpResponse("MIT$" + user.name())
    
    return HttpResponse("NON-MIT$" + user.name())

@admin_required
def list_budget_categories(request):
    service = create_google_service()
    return HttpResponse('OK')


def create_google_service():
    credentials = OAuth2Credentials.from_json(settings.GOOGLE_CREDENTIALS)
    
    http = httplib2.Http()
    http = credentials.authorize(http)
    
    service = build("drive", "v2", http=http)
    return service
