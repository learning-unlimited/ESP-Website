from django.conf.urls.defaults import *

urlpatterns = patterns('esp.miniblog.views',
                     
                     # Mini-Blog pages
                       (r'^(?P<subsection>(learn|teach|program|help|manage|onsite))/(?P<url>.*).blog$', 'single_blog_entry'),
                       (r'^(?P<url>.*).blog$', 'single_blog_entry'),

)
