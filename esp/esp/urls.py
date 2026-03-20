__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from django.urls import include, path, re_path
from django.contrib import admin
from esp.admin import admin_site, autodiscover
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from filebrowser.sites import site as filebrowser_site

# main list of apps
import argcache.urls
import debug_toolbar
import esp.accounting.urls
import esp.customforms.urls
import esp.formstack.urls
import esp.program.urls
import esp.qsdmedia.urls
import esp.random.urls
import esp.survey.urls
import esp.tests.urls
import esp.themes.urls
import esp.users.urls
import esp.varnish.urls

#TODO: move these out of the main urls.py
from esp.web.views import main
import esp.qsd.views
import esp.db.views
import esp.users.views
import esp.utils.views

autodiscover(admin_site)

# Override error pages
handler404 = 'esp.utils.web.error404'
handler500 = 'esp.utils.web.error500'

# Static media
urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + staticfiles_urlpatterns()

# Robots.txt
urlpatterns += [
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain"))
]

# Admin stuff
urlpatterns += [
    re_path(r'^admin_tools/', include('admin_tools.urls')),
    re_path(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    re_path(r'^admin/ajax_qsd/?$', esp.qsd.views.ajax_qsd),
    re_path(r'^admin/ajax_qsd_preview/?$', esp.qsd.views.ajax_qsd_preview),
    re_path(r'^admin/ajax_qsd_history/?$', esp.qsd.views.ajax_qsd_history),
    re_path(r'^admin/ajax_qsd_version_preview/?$', esp.qsd.views.ajax_qsd_version_preview),
    re_path(r'^admin/ajax_qsd_restore/?$', esp.qsd.views.ajax_qsd_restore),
    re_path(r'^admin/ajax_qsd_image_upload/?$', esp.qsd.views.ajax_qsd_image_upload),
    re_path(r'^admin/ajax_autocomplete/?', esp.db.views.ajax_autocomplete),
    re_path(r'^admin/filebrowser/', filebrowser_site.urls),
    re_path(r'^admin/', admin_site.urls),
    re_path(r'^accounts/login/$', esp.users.views.CustomLoginView.as_view()),
    re_path(r'^(?P<subsection>(learn|teach|program|help|manage|onsite))/?$', RedirectView.as_view(url='/%(subsection)s/index.html', permanent=True)),
]

# Adds missing trailing slash to any admin urls that haven't been matched yet.
urlpatterns += [
    re_path(r'^(?P<url>admin($|(.*[^/]$)))', RedirectView.as_view(url='/%(url)s/', permanent=True))]

# generic stuff
urlpatterns += [
    re_path(r'^$', main.home), # index
    re_path(r'^set_csrf_token', main.set_csrf_token), # tiny view used to set csrf token
]

# main list of apps (please consolidate more things into this!)
urlpatterns += [
    re_path(r'^cache/', include(argcache.urls)),
    re_path(r'^__debug__/', include(debug_toolbar.urls)),
    re_path(r'^accounting/', include(esp.accounting.urls)),
    re_path(r'^customforms', include(esp.customforms.urls)),
    re_path(r'^random', include(esp.random.urls)),
    re_path(r'^', include(esp.formstack.urls)),
    re_path(r'^',  include(esp.program.urls)),
    re_path(r'^download', include(esp.qsdmedia.urls)),
    re_path(r'^',  include(esp.survey.urls)),
    re_path('^javascript_tests', include(esp.tests.urls)),
    re_path(r'^themes', include(esp.themes.urls)),
    re_path(r'^myesp/', include(esp.users.urls)),
    re_path(r'^varnish/', include(esp.varnish.urls)),
]

urlpatterns += [
    # bios
    re_path(r'^(?P<tl>teach|learn)/teachers/', include('esp.web.urls')),
]

# Specific .html pages that have defaults
urlpatterns += [
    re_path(r'^(faq|faq\.html)$', main.FAQView.as_view(), name='FAQ'),
    re_path(r'^(contact|contact\.html)$', main.ContactUsView.as_view(), name='Contact Us'),
]

urlpatterns += [
    re_path(r'^(?P<url>.*)\.html$', esp.qsd.views.qsd),
]

# QSD Media
# aseering 8/14/2007: This ought to be able to be written in a simpler way...
urlpatterns += [
    # aseering - Is it worth consolidating these?  Two entries for the single "contact us! widget
    # Contact Us! pages
    re_path(r'^contact/contact/?$', main.contact),
    re_path(r'^contact/contact/(?P<section>[^/]+)/?$', main.contact),

    # Program stuff
    re_path(r'^(onsite|manage|teach|learn|volunteer|json)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.program),
    re_path(r'^(onsite|manage|teach|learn|volunteer|json)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.program),

    # all the archives
    re_path(r'^archives/([-A-Za-z0-9_ ]+)/?$', main.archives),
    re_path(r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.archives),
    re_path(r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.archives),

    re_path(r'^email/([0-9]+)/?$', main.public_email),
]

urlpatterns += [
re_path(r'^(?P<subsection>onsite|manage|teach|learn|volunteer)/(?P<program>[-A-Za-z0-9_ ]+)/?$', RedirectView.as_view(url='/%(subsection)s/%(program)s/index.html', permanent=True))]


urlpatterns += [
    re_path(r'^manage/templateoverride/(?P<template_id>[0-9]+)',
        esp.utils.views.diff_templateoverride),
]
