from django.conf.urls.defaults import *
from dataviews.views import wizard_view

urlpatterns = patterns('esp.dataviews',
    (r'^$', wizard_view)
)
