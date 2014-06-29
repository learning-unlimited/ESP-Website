from django.conf.urls.defaults import *
from esp.dataviews.views import wizard_view, mode_view, doc_view, path_view
from esp.dataviews import useful_models

useful_models_text = r'|'.join([useful_model.__name__ for useful_model in useful_models])

urlpatterns = patterns('esp.dataviews',
    (r'^mode(?P<mode>\d{2})/$', mode_view),
    (r'^(?P<model_name>%s)/$' % useful_models_text, doc_view),
    (r'^(?P<model1_name>%s)/(?P<model2_name>%s)/$' % (useful_models_text,useful_models_text), path_view),
    (r'^$', wizard_view),
)
