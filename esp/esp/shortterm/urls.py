from django.conf.urls.defaults import *

urlpatterns = patterns('esp.shortterm.views',
                       (r'^school_response/?', 'school_response_form'),
                       (r'^volunteer/signup/?$', 'volunteer_signup',),
                       (r'^survey_results/$', 'excel_survey_responses'),
					   (r'^logistics_quiz_start/?$', 'logistics_quiz_start'),
					   (r'^logistics_quiz_check/?$', 'logistics_quiz_check'),
                       )
