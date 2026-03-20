from django.urls import re_path
from esp.survey.views import survey_view, teacher_survey_all


urlpatterns = [
    # Cross-program teacher survey responses
    re_path(r'^myesp/survey_responses/?$', teacher_survey_all, name='teacher_survey_all'),
    # Program stuff
    re_path(r'^(onsite|manage|teach|learn)/(.*?)/(.*?)/program.survey$', survey_view),
]
