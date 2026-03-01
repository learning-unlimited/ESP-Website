from django.conf.urls import url

from esp.program import views
import esp.users.views.merge
import esp.dbmail.views as inbox_views

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
    url(r'^manage/catsflagsrecs/?(?P<section>[^/]*)/?$', views.catsflagsrecs),
    url(r'^manage/tags/?(?P<section>[^/]*)/?$', views.tags),
    url(r'^manage/redirects/?(?P<section>[^/]*)/?$', views.redirects),
    url(r'^manage/statistics/?$', views.statistics),
    url(r'^manage/preview/?$', views.template_preview),
    url(r'^manage/mergeaccounts/?$', esp.users.views.merge.merge_accounts),

    # Shared email inbox (Issue #3831)
    url(r'^manage/inbox/?$', inbox_views.inbox),
    url(r'^manage/inbox/thread/(?P<thread_id>\d+)/?$', inbox_views.inbox_thread),
    url(r'^manage/inbox/thread/(?P<thread_id>\d+)/mark-read/?$', inbox_views.inbox_mark_read),
    url(r'^manage/inbox/thread/(?P<thread_id>\d+)/update/?$', inbox_views.inbox_update_thread),
    url(r'^manage/inbox/attachment/(?P<attachment_id>\d+)/?$', inbox_views.inbox_attachment),
]
