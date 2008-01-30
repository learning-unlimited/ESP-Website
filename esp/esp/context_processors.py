import esp.web.util.globaltags
from django.contrib.sites.models import Site
from django.conf import settings

def media_url(request): 
    return {'media_url': settings.MEDIA_URL} 

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

def auth(request):

    if request.path.startswith('/admin'):
        return {
            'user': request.user,
            'messages': request.user.get_and_delete_messages(),
            'perms': PermWrapper(request.user)
            }          

    return {
        'user': request.user,
        }


def current_site(request):

    if hasattr(settings, 'SITE_INFO'):
        return {'current_site': Site(*settings.SITE_INFO) }

    return {'current_site': Site.objects.get_current()}

    
# PermWrapper and PermLookupDict proxy the permissions system into objects that
# the template system can understand.

class PermLookupDict(object):
    def __init__(self, user, module_name):
        self.user, self.module_name = user, module_name

    def __repr__(self):
        return str(self.user.get_all_permissions())

    def __getitem__(self, perm_name):
        return self.user.has_perm("%s.%s" % (self.module_name, perm_name))

    def __nonzero__(self):
        return self.user.has_module_perms(self.module_name)

class PermWrapper(object):
    def __init__(self, user):
        self.user = user

    def __getitem__(self, module_name):
        return PermLookupDict(self.user, module_name)
