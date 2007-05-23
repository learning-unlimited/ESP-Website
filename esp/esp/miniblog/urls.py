from django.conf.urls.defaults import *

urlpatterns = patterns('esp.miniblog.views',
                     
                     # Mini-Blog pages
                     # These are broken...must fix (axiak)
                     #(r'^(?P<subsection>teach|learn|help)/(?P<url>.*)/blog/$', 'esp.miniblog.views.show_miniblog', {'section_redirect_keys': section_redirect_keys}),
                     (r'^(?P<url>.*)/post/$', 'post_miniblog'),
                     (r'^(?P<url>.*)/$', 'show_miniblog_entry'),
                     (r'^$', 'show_miniblog', {'url': '', 'section_redirect_keys': section_redirect_keys}),
)
