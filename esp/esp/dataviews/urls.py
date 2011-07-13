from django.conf.urls.defaults import *
from dataviews.forms import ModeForm, DataViewsWizard

urlpatterns = patterns('esp.dataviews',
    (r'^$', DataViewsWizard([ModeForm]))
)
