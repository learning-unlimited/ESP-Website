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

def preload_images(request):
    return {'preload_images': preload_images_data}

preload_images_data = [
	settings.MEDIA_URL+'images/level3/nav/home_ro.gif',
	settings.MEDIA_URL+'images/level3/nav/discoveresp_ro.gif',
	settings.MEDIA_URL+'images/level3/nav/takeaclass_ro.gif',
	settings.MEDIA_URL+'images/level3/nav/volunteertoteach_ro.gif',
	settings.MEDIA_URL+'images/level3/nav/getinvolved_ro.gif',
	settings.MEDIA_URL+'images/level3/nav/archivesresources_ro.gif',
	settings.MEDIA_URL+'images/level3/nav/myesp_ro.gif',
	settings.MEDIA_URL+'images/level3/nav/contactinfo_ro.gif'
]
