from django.conf import settings
from django.http import HttpResponse, Http404

from esp.users.models import admin_required, ESPUser

import gdata.gauth
import gdata.spreadsheets.client

OAUTH_SCOPES = [ "https://spreadsheets.google.com/feeds",
    "https://docs.google.com/feeds" ]
USER_AGENT = ""

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
    ss_client = create_ss_service()
    worksheets = ss_client.get_worksheets(
        spreadsheet_key=settings.BUDGET_SPREADSHEET_KEY)

    return HttpResponse(worksheets.entry[0].to_string())

def create_ss_service():
    token = gdata.gauth.token_from_blob(settings.GOOGLE_CREDENTIALS)
    ss_client = gdata.spreadsheets.client.SpreadsheetsClient(source=USER_AGENT)
    ss_client = token.authorize(ss_client)
    return ss_client
