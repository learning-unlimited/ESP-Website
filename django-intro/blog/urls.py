from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^blog/', include('blog.apps.foo.urls.foo')),

    # Uncomment this for admin:
     (r'^admin/', include('django.contrib.admin.urls')),
     (r'^/$', 'blog.myblog.views.list_blogs'),
)
