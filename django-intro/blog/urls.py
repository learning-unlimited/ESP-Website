from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^blog/', include('blog.apps.foo.urls.foo')),

    # This gives us our admin interface at http://localhost:8000/admin/
     (r'^admin/', include('django.contrib.admin.urls')),

    # This gives us our list of blog entries at http://localhost:8000/
     (r'^$', 'blog.myblog.views.list_blogs'),

    # This gives us our images from our media/ folder at http://localhost:8000/media/
    # NOTE: On a real site, you'd actually let the web server handle this.
     (r'^static/(.*)$', 'django.views.static.serve', {'document_root': 'media'}),
)
