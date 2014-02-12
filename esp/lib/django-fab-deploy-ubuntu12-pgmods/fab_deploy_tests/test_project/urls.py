from django.conf.urls.defaults import *
from django.http import HttpResponse
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^instance/', lambda r: HttpResponse(settings.INSTANCE_NAME)),
)
