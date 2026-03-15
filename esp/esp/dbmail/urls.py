from django.conf.urls import url
import esp.dbmail.views

urlpatterns = [
    url(r'^email/([0-9]+)/?$', esp.dbmail.views.public_email),
]