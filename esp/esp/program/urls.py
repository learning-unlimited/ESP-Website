from django.conf.urls import url

from esp.program import views
import esp.users.views.merge

urlpatterns = [
    # manage stuff
    url(r'^manage/programs/?$', views.manage_programs, name='manage_programs'),
    url(r'^manage/newprogram/?$', views.newprogram, name='manage_newprogram'),
    url(r'^manage/submit_transaction/?$', views.submit_transaction, name='manage_submit_transaction'),
    url(r'^manage/pages/?$', views.manage_pages, name='manage_pages'),
    url(r'^manage/userview/?$', views.userview, name='manage_userview'),
    url(r'^manage/deactivate_user/?$', views.deactivate_user, name='manage_deactivate_user'),
    url(r'^manage/activate_user/?$', views.activate_user, name='manage_activate_user'),
    url(r'^manage/unenroll_student/?$', views.unenroll_student, name='manage_unenroll_student'),
    url(r'^manage/usersearch/?$', views.usersearch, name='manage_usersearch'),
    url(r'^manage/flushcache/?$', views.flushcache, name='manage_flushcache'),
    url(r'^manage/emails/?$', views.emails, name='manage_emails'),
    url(r'^manage/catsflagsrecs/?(?P<section>[^/]*)/?$', views.catsflagsrecs, name='manage_catsflagsrecs'),
    url(r'^manage/tags/?(?P<section>[^/]*)/?$', views.tags, name='manage_tags'),
    url(r'^manage/redirects/?(?P<section>[^/]*)/?$', views.redirects, name='manage_redirects'),
    url(r'^manage/statistics/?$', views.statistics, name='manage_statistics'),
    url(r'^manage/preview/?$', views.template_preview, name='manage_template_preview'),
    url(r'^manage/mergeaccounts/?$', esp.users.views.merge.merge_accounts, name='manage_mergeaccounts'),
]
