from django.urls import re_path

from esp.program import views
import esp.users.views.merge

urlpatterns = [
    # manage stuff
    re_path(r'^manage/programs/?$', views.manage_programs),
    re_path(r'^manage/newprogram/?$', views.newprogram),
    re_path(r'^manage/submit_transaction/?$', views.submit_transaction),
    re_path(r'^manage/pages/?$', views.manage_pages),
    re_path(r'^manage/userview/?$', views.userview),
    re_path(r'^manage/deactivate_user/?$', views.deactivate_user),
    re_path(r'^manage/activate_user/?$', views.activate_user),
    re_path(r'^manage/unenroll_student/?$', views.unenroll_student),
    re_path(r'^manage/usersearch/?$', views.usersearch),
    re_path(r'^manage/flushcache/?$', views.flushcache),
    re_path(r'^manage/emails/?$', views.emails),
    re_path(r'^manage/catsflagsrecs/?(?P<section>[^/]*)/?$', views.catsflagsrecs),
    re_path(r'^manage/tags/?(?P<section>[^/]*)/?$', views.tags),
    re_path(r'^manage/redirects/?(?P<section>[^/]*)/?$', views.redirects),
    re_path(r'^manage/statistics/?$', views.statistics),
    re_path(r'^manage/preview/?$', views.template_preview),
    re_path(r'^manage/mergeaccounts/?$', esp.users.views.merge.merge_accounts),
    re_path(r'^manage/docs(?:/(?P<doc_path>.*))?/?$', views.manage_docs),
]
