"""
URL patterns for Teacher Application Module
"""

from django.urls import re_path
from esp.program.modules.handlers.teacherappmodule import (
    my_applications,
    create_application,
    edit_application,
    manage_questions,
    review_applications,
    approve_application,
    reject_application,
)

urlpatterns = [
    # Teacher views
    re_path(r'^my-applications/$', my_applications, name='teacherapp_my_applications'),
    re_path(r'^create/(?P<subject_id>\d+)/$', create_application, name='teacherapp_create_application'),
    re_path(r'^edit/(?P<app_id>\d+)/$', edit_application, name='teacherapp_edit_application'),
    
    # Admin views
    re_path(r'^manage-questions/$', manage_questions, name='teacherapp_manage_questions'),
    re_path(r'^review-applications/$', review_applications, name='teacherapp_review_applications'),
    re_path(r'^approve/(?P<app_id>\d+)/$', approve_application, name='teacherapp_approve_application'),
    re_path(r'^reject/(?P<app_id>\d+)/$', reject_application, name='teacherapp_reject_application'),
]
