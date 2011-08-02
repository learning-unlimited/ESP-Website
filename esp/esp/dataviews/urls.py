from django.conf.urls.defaults import *
from dataviews.views import wizard_view, mode_view

urlpatterns = patterns('esp.dataviews',
    (r'^mode(?P<mode>\d{2})/$', mode_view),
    (r'^$', wizard_view),
)
