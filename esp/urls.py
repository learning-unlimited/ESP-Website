from django.conf.urls.defaults import *
from esp.program.models import Claus

urlpatterns = patterns('',
    (r'^startaclass/', 'django.views.generic.create_update.create_object', { 'model': Claus } ),
    # Example:
    # (r'^esp/', include('esp.apps.foo.urls.foo')),

    # The default
    (r'^$', 'esp.web.views.index'),
    (r'^contact.html$', 'esp.web.views.contact'),
    (r'^Learn/teachers/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/bio.html$', 'esp.web.views.bio'),
    (r'^Programs/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/catalogue/?$', 'esp.program.views.courseCatalogue'),
    (r'^myesp/([-A-Za-z0-9_ ]+)/?$', 'esp.web.views.myesp'),                       
    (r'^(?P<url>.*)\.html$', 'esp.web.views.qsd'),
    (r'^(?P<url>.*)\.text$', 'esp.web.views.qsd_raw'),

    # Uncomment this for admin:
     (r'^admin/', include('django.contrib.admin.urls')),
)
