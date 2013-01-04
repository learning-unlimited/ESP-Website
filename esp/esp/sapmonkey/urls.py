from django.conf.urls.defaults import *

urlpatterns = patterns('esp.sapmonkey.views',
    (r'^check_auth$', 'check_auth'),
    (r'^lookup_username/(?P<username>.*)$', 'lookup_username'),
    (r'^list_budget_categories$', 'list_budget_categories'),
    (r'^list_classes/(?P<program>.*)/all$', 'list_classes', {'select': 'all', 'username': None}),
    (r'^list_classes/(?P<program>.*)/(?P<select>only|priority)/(?P<username>.*)$', 'list_classes'),
)

