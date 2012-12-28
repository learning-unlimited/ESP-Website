from django.conf import settings
import gdata.gauth

OAUTH_SCOPES = [ "https://spreadsheets.google.com/feeds",
    "https://docs.google.com/feeds" ]
USER_AGENT = ""
REDIRECT_URL = "urn:ietf:wg:oauth:2.0:oob"

token = gdata.gauth.OAuth2Token(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    scope=" ".join(OAUTH_SCOPES),
    user_agent=USER_AGENT)

print "Visit this URL to authorize:"
print ""
print token.generate_authorize_url(redirect_url=REDIRECT_URL)
print ""

code = raw_input("Access Code: ")
token.get_access_token(code)

print ""
print "This is your token. Save it to the configuration variable GOOGLE_CREDENTIALS:"
print gdata.gauth.token_to_blob(token)
