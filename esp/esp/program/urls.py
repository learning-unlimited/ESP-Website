from django.conf.urls.defaults import *

urlpatterns = patterns('',
                       # manage stuff
                       (r'^manage/programs/?$', 'esp.program.views.manage_programs'),
                       (r'^manage/newprogram/?$', 'esp.program.views.newprogram'),
                       (r'^manage/submit_transaction/?$', 'esp.program.views.submit_transaction'),
                       (r'^manage/pages/?$', 'esp.program.views.manage_pages'),
                       (r'^manage/userview/?$', 'esp.program.views.userview'),
                       )
