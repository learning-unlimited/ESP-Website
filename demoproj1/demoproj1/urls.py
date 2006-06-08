from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^demoproj1/', include('demoproj1.apps.foo.urls.foo')),

    # Uncomment this for admin:
                       (r'^admin/', include('django.contrib.admin.urls')),
                       (r'^polls/$', 'demoproj1.polls.views.index'),
                       (r'^polls/(?P<poll_id>\d+)/$', 'demoproj1.polls.views.detail'),
                       (r'^polls/(?P<poll_id>\d+)/results/$', 'demoproj1.polls.views.results'),
                       (r'^polls/(?P<poll_id>\d+)/vote/$', 'demoproj1.polls.views.vote'),
)
