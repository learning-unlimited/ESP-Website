from django.conf.urls import url
from esp.survey.views import survey_view, teacher_survey_all


urlpatterns = [
    # Cross-program teacher survey responses
    url(r'^myesp/survey_responses/?$', teacher_survey_all, name='teacher_survey_all'),
    # Program stuff
    url(r'^(onsite|manage|teach|learn)/(.*?)/(.*?)/program.survey$', survey_view),
]
