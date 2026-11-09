from django.urls import re_path
from esp.survey.views import survey_view, teacher_survey_all


urlpatterns = [
    # Cross-program teacher survey responses
    re_path(r'^myesp/survey_responses/?$', teacher_survey_all, name='teacher_survey_all'),
    # Program stuff
    re_path(r'^(?P<tl>onsite|manage|teach|learn|survey)/(?P<program>.*?)/(?P<instance>.*?)/program.survey$', survey_view, name='program_survey'),
    re_path(r'^survey/(?P<program>[-A-Za-z0-9_ ]+)/(?P<instance>[-A-Za-z0-9_ ]+)(?:/|/survey)?/?$', survey_view, {'tl': 'generic'}, name='generic_program_survey'),
]
