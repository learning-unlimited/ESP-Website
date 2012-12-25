from apiclient.discovery import build
from oauth2client.client import OAuth2WebServerFlow

from django.conf import settings

OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'
REDIRECT_URL = 'urn:ietf:wg:oauth:2.0:oob'

flow = OAuth2WebServerFlow(settings.GOOGLE_CLIENT_ID,
    settings.GOOGLE_CLIENT_SECRET, OAUTH_SCOPE, REDIRECT_URL)
authorize_url = flow.step1_get_authorize_url()
print '\nGo to the following link in your browser:\n' + authorize_url
code = raw_input('Enter verification code: ').strip()
credentials = flow.step2_exchange(code)

print '\nPlace the following code in settings.GOOGLE_CREDENTIALS:\n'
print credentials.to_json()
