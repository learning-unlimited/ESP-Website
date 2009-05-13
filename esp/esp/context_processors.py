import esp.web.util.globaltags
from django.contrib.sites.models import Site
from django.conf import settings

def media_url(request): 
    return {'media_url': settings.MEDIA_URL} 

def espuserified_request(request):
    from esp.users.models import ESPUser
    if hasattr(request, 'user'):
        # Forces the user object to be an ESPUser object
        request.user = ESPUser(request.user, error=True)
        request.user.updateOnsite(request)
    return {'request': request}

def esp_user(request):
    from esp.users.models import ESPUser
    if hasattr(request, 'user'):
        user = ESPUser(request.user)
        return {'user': user}
    return {}

def test_cookie(request):

    if not request.user.is_authenticated():
        request.session.set_test_cookie()
    return {}

def index_backgrounds(request):
    #if request.path.strip() == '':
    return {'backgrounds': ["/media/images/home/pagebkg1.jpg",
                            "/media/images/home/pagebkg2.jpg",
                            "/media/images/home/pagebkg3.jpg"]}
    return {}

def current_site(request):

    if hasattr(settings, 'SITE_INFO'):
        return {'current_site': Site(*settings.SITE_INFO) }

    return {'current_site': Site.objects.get_current()}
