from django.conf.urls import url

from esp.program import views
import esp.users.views.merge

urlpatterns = [
    # manage stuff
    url(r'^manage/programs/?$', views.manage_programs),
    url(r'^manage/newprogram/?$', views.newprogram),
    url(r'^manage/submit_transaction/?$', views.submit_transaction),
    url(r'^manage/pages/?$', views.manage_pages),
    url(r'^manage/userview/?$', views.userview),
    url(r'^manage/deactivate_user/?$', views.deactivate_user),
    url(r'^manage/activate_user/?$', views.activate_user),
    url(r'^manage/unenroll_student/?$', views.unenroll_student),
    url(r'^manage/usersearch/?$', views.usersearch),
    url(r'^manage/flushcache/?$', views.flushcache),
    url(r'^manage/emails/?$', views.emails),
    url(r'^manage/tags/?(?P<section>[^/]*)/?$', views.tags),
    url(r'^manage/statistics/?$', views.statistics),
    url(r'^manage/preview/?$', views.template_preview),
    url(r'^manage/mergeaccounts/?$', esp.users.views.merge.merge_accounts),
]
