from django.urls import re_path

from esp.program import views
import esp.users.views.merge

urlpatterns = [
    # manage stuff
    re_path(r'^manage/programs/?$', views.manage_programs, name='manage_programs'),
    re_path(r'^manage/newprogram/?$', views.newprogram, name='manage_newprogram'),
    re_path(r'^manage/submit_transaction/?$', views.submit_transaction, name='manage_submit_transaction'),
    re_path(r'^manage/pages/?$', views.manage_pages, name='manage_pages'),
    re_path(r'^manage/userview/?$', views.userview, name='manage_userview'),
    re_path(r'^manage/deactivate_user/?$', views.deactivate_user, name='manage_deactivate_user'),
    re_path(r'^manage/activate_user/?$', views.activate_user, name='manage_activate_user'),
    re_path(r'^manage/unenroll_student/?$', views.unenroll_student, name='manage_unenroll_student'),
    re_path(r'^manage/usersearch/?$', views.usersearch, name='manage_usersearch'),
    re_path(r'^manage/flushcache/?$', views.flushcache, name='manage_flushcache'),
    re_path(r'^manage/emails/?$', views.emails, name='manage_emails'),
    re_path(r'^manage/catsflagsrecs/?(?P<section>[^/]*)/?$', views.catsflagsrecs, name='manage_catsflagsrecs'),
    re_path(r'^manage/tags/?(?P<section>[^/]*)/?$', views.tags, name='manage_tags'),
    re_path(r'^manage/redirects/?(?P<section>[^/]*)/?$', views.redirects, name='manage_redirects'),
    re_path(r'^manage/statistics/?$', views.statistics, name='manage_statistics'),
    re_path(r'^manage/preview/?$', views.template_preview, name='manage_template_preview'),
    re_path(r'^manage/mergeaccounts/?$', esp.users.views.merge.merge_accounts, name='manage_mergeaccounts'),
    re_path(r'^manage/docs(?:/(?P<doc_path>.*))?/?$', views.manage_docs, name='manage_docs'),
]
