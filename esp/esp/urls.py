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

from django.conf.urls import include, handler500, handler404, url
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

# Admin stuff
urlpatterns += [
    url(r'^admin_tools/', include('admin_tools.urls')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/ajax_qsd/?$', esp.qsd.views.ajax_qsd),
    url(r'^admin/ajax_qsd_preview/?$', esp.qsd.views.ajax_qsd_preview),
    url(r'^admin/ajax_autocomplete/?', esp.db.views.ajax_autocomplete),
    url(r'^admin/filebrowser/', include(filebrowser_site.urls)),
    url(r'^admin/', include(admin_site.urls)),
    url(r'^accounts/login/$', esp.users.views.login_checked),
    url(r'^(?P<subsection>(learn|teach|program|help|manage|onsite))/?$',RedirectView.as_view(url='/%(subsection)s/index.html', permanent=True)),
]

# Adds missing trailing slash to any admin urls that haven't been matched yet.
urlpatterns += [
    url(r'^(?P<url>admin($|(.*[^/]$)))', RedirectView.as_view(url='/%(url)s/', permanent=True))]

# generic stuff
urlpatterns += [
    url(r'^$', main.home), # index
    url(r'^set_csrf_token', main.set_csrf_token), # tiny view used to set csrf token
]

# main list of apps (please consolidate more things into this!)
urlpatterns += [
    url(r'^cache/', include(argcache.urls)),
    url(r'^__debug__/', include(debug_toolbar.urls)),
    url(r'^accounting/', include(esp.accounting.urls)),
    url(r'^customforms', include(esp.customforms.urls)),
    url(r'^random', include(esp.random.urls)),
    url(r'^', include(esp.formstack.urls)),
    url(r'^',  include(esp.program.urls)),
    url(r'^download', include(esp.qsdmedia.urls)),
    url(r'^',  include(esp.survey.urls)),
    url('^javascript_tests', include(esp.tests.urls)),
    url(r'^themes', include(esp.themes.urls)),
    url(r'^myesp/', include(esp.users.urls)),
    url(r'^varnish/', include(esp.varnish.urls)),
]

urlpatterns += [
    # bios
    url(r'^(?P<tl>teach|learn)/teachers/', include('esp.web.urls')),
]

# Specific .html pages that have defaults
urlpatterns += [
    url(r'^faq', TemplateView.as_view(template_name='faq.html'), name='FAQ'),
]

urlpatterns += [
    url(r'^(?P<url>.*)\.html$', esp.qsd.views.qsd),
]

# QSD Media
# aseering 8/14/2007: This ought to be able to be written in a simpler way...
urlpatterns += [
    # aseering - Is it worth consolidating these?  Two entries for the single "contact us! widget
    # Contact Us! pages
    url(r'^contact/contact/?$', main.contact),
    url(r'^contact/contact/(?P<section>[^/]+)/?$', main.contact),

    # Program stuff
    url(r'^(onsite|manage|teach|learn|volunteer|json)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.program),
    url(r'^(onsite|manage|teach|learn|volunteer|json)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.program),

    # all the archives
    url(r'^archives/([-A-Za-z0-9_ ]+)/?$', main.archives),
    url(r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.archives),
    url(r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.archives),

    url(r'^email/([0-9]+)/?$', main.public_email),
]

urlpatterns += [
url(r'^(?P<subsection>onsite|manage|teach|learn|volunteer)/(?P<program>[-A-Za-z0-9_ ]+)/?$', RedirectView.as_view(url='/%(subsection)s/%(program)s/index.html', permanent=True))]


urlpatterns += [
    url(r'^manage/templateoverride/(?P<template_id>[0-9]+)',
        esp.utils.views.diff_templateoverride),
]
