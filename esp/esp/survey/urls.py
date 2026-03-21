from django.urls import re_path
from esp.survey.views import survey_view


urlpatterns = [
    # Program stuff
    re_path(r'^(onsite|manage|teach|learn)/(.*?)/(.*?)/program.survey$', survey_view, name='program_survey'),
]
