from django.conf.urls import url
from esp.survey.views import survey_view


urlpatterns = [
    # Program stuff
    url(r'^(onsite|manage|teach|learn)/(.*?)/(.*?)/program.survey$', survey_view),
]
