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
    return {'user': lambda: request.user}
    return {}

def index_backgrounds(request):
    #if request.path.strip() == '':
    return {'backgrounds': [settings.MEDIA_URL+"images/home/pagebkg1.jpg",
                            settings.MEDIA_URL+"images/home/pagebkg2.jpg",
                            settings.MEDIA_URL+"images/home/pagebkg3.jpg"]}
    return {}

def current_site(request):

    if hasattr(settings, 'SITE_INFO'):
        return {'current_site': Site(*settings.SITE_INFO) }

    return {'current_site': Site.objects.get_current()}

def preload_images(request):
    return {'preload_images': preload_images_data}

""" This list can be populated with images to be preloaded by the template.
    
    Example:
    preload_images_data = [
        settings.MEDIA_URL+'images/level3/nav/home_ro.gif',
        settings.MEDIA_URL+'images/level3/nav/discoveresp_ro.gif',
        (etc.)
        ] 
"""

preload_images_data = [
]
