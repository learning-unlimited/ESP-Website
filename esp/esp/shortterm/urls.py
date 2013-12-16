from django.conf.urls import *

urlpatterns = patterns('esp.shortterm.views',
                       (r'^school_response/?', 'school_response_form'),
                       (r'^survey_results/$', 'excel_survey_responses'),
                       )
