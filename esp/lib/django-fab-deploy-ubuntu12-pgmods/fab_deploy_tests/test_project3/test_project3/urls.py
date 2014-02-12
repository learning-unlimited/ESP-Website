from django.conf.urls import patterns, include, url
from django.http import HttpResponse
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^instance/', lambda r: HttpResponse(settings.INSTANCE_NAME)),
    url(r'^app/', include('test_project3.app.urls')),
)

if settings.GEO:
    urlpatterns += patterns('',
        url(r'^geo/', include('test_project3.geo_app.urls')),
    )
