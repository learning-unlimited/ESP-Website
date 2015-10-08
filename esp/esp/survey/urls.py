from django.conf.urls import *
from esp.survey.views import survey_view


urlpatterns = patterns('',
                       # Program stuff
                       (r'^(onsite|manage|teach|learn)/(.*?)/(.*?)/program.survey$', survey_view),
                       )
