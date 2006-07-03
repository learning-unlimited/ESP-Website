from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^esp/', include('esp.apps.foo.urls.foo')),

    # The default
    (r'^$', 'esp.web.views.index'),
    (r'^(?P<url>.*)\.html$', 'esp.web.views.qsd'),
    (r'^(?P<url>.*)\.text$', 'esp.web.views.qsd_raw'),

    # Uncomment this for admin:
     (r'^admin/', include('django.contrib.admin.urls')),
)
