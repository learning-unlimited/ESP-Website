from django.conf.urls import url

from esp.dbmail import views

urlpatterns = [
    url(r'^webhooks/sendgrid/?$', views.sendgrid_webhook),
]
