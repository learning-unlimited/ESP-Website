from django.conf.urls.defaults import *
from dataviews.forms import ModeForm, HeadingConditionsForm, DisplayColumnForm, DataViewsWizard

urlpatterns = patterns('esp.dataviews',
    (r'^$', DataViewsWizard([ModeForm, HeadingConditionsForm, DisplayColumnForm]))
)
