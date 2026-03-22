"""
URL patterns for dbmail email preview functionality
"""

from django.urls import path
from esp.dbmail import views

urlpatterns = [
    path('preview/<int:message_request_id>/', views.preview_email, name='preview_email'),
    path('send_test/<int:message_request_id>/', views.send_test_email, name='send_test_email'),
]
