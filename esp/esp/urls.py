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
from django.conf.urls.defaults import patterns, include, url, handler500, handler404
from esp.admin import admin_site, autodiscover
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView
from filebrowser.sites import site as filebrowser_site
import debug_toolbar

autodiscover(admin_site)

# Override error pages
handler404 = 'esp.web.util.main.error404'
handler500 = 'esp.web.util.main.error500'

# Static media
urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + staticfiles_urlpatterns()

# Admin stuff
urlpatterns += patterns('',
                     (r'^admin/doc/', include('django.contrib.admindocs.urls')),
                     (r'^admin/ajax_qsd/?', 'esp.qsd.views.ajax_qsd'),
                     (r'^admin/ajax_autocomplete/?', 'esp.db.views.ajax_autocomplete'),
                     (r'^grappelli/', include('grappelli.urls')),
                     (r'^admin/filebrowser/', include(filebrowser_site.urls)),
                     (r'^admin/', include(admin_site.urls)),
                     (r'^accounts/login/$', 'esp.users.views.login_checked',),
                     #(r'^learn/Junction/2007_Spring/catalog/?$',RedirectView.as_view(url='/learn/Junction/2007_Summer/catalog/')),
                     (r'^(?P<subsection>(learn|teach|program|help|manage|onsite))/?$',RedirectView.as_view(url='/%(subsection)s/index.html')),
                        )

# Adds missing trailing slash to any admin urls that haven't been matched yet.
urlpatterns += patterns('',
(r'^(?P<url>admin($|(.*[^/]$)))', RedirectView.as_view(url='/%(url)s/')),)

# generic stuff
urlpatterns += patterns('esp.web.views.main',
                        (r'^error_reporter', 'error_reporter'),
                        (r'^$', 'home'), # index
                        (r'^set_csrf_token', 'set_csrf_token'), # tiny view used to set csrf token
                        )

# program stuff
urlpatterns += patterns('',
                        (r'^',  include('esp.program.urls')),
                        )

urlpatterns += patterns('esp.web.views.bio',

                        # bios
                        (r'^(?P<tl>teach|learn)/teachers/(?P<last>[-A-Za-z0-9_ \.]+)/(?P<first>[-A-Za-z_ \.]+)(?P<usernum>[0-9]*)/bio\.html$', 'bio'),
                        (r'^(?P<tl>teach|learn)/teachers/(?P<username>[^/]+)/bio\.html$', 'bio'),
                        (r'^myesp/teacherbio/?$', 'bio_edit'),
                        (r'^(?P<tl>teach|learn)/teachers/(?P<last>[-A-Za-z0-9_ ]+)/(?P<first>[-A-Za-z_ ]+)(?P<usernum>[0-9]*)/bio\.edit\.html/?(.*)$', 'bio_edit'),
                        (r'^(?P<tl>teach|learn)/teachers/(?P<username>[^/]+)/bio\.edit\.html/?(.*)$', 'bio_edit'),
                        )

urlpatterns += patterns('',
                        (r'^myesp/', include('esp.users.urls'),)
                        )

urlpatterns += patterns('',
                        (r'^cache/', include('esp.cache.urls')),
                        (r'^varnish/', include('esp.varnish.urls'))
                        )

urlpatterns += patterns('esp.qsd.views',
                        #(r'^(?P<subsection>(learn|teach|programs|manage|onsite))/(?P<url>.*)\.html$', 'qsd'),
                        (r'^(?P<url>.*)\.html$', 'qsd'),
                        )

#urlpatterns += patterns('',
#                        (r'^(?P<subsection>(learn|teach|programs|manage|onsite))/?$', RedirectView.as_view(url='/%(subsection)s/index.html')),
#                        )

# other apps
urlpatterns += patterns('',
                        (r'^',  include('esp.survey.urls')),
                        )

urlpatterns += patterns('esp.web.views.json',

     # JSON
    (r'json/teachers/$', 'teacher_lookup'))

# QSD Media
# aseering 8/14/2007: This ought to be able to be written in a simpler way...
urlpatterns += patterns('esp.web.views.main',

    # aseering - Is it worth consolidating these?  Two entries for the single "contact us! widget
    # Contact Us! pages
    (r'^contact/contact/?$', 'contact'),
    (r'^contact/contact/(?P<section>[^/]+)/?$', 'contact'),
#    (r'^contact/submit\.html$', 'contact_submit'),

    # Generic "thank you for submitting" page
    (r'^thanks/$', 'thanks'),

    # Program stuff
    (r'^(onsite|manage|teach|learn|volunteer)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/classchangerequest/?$', 'classchangerequest'),
    (r'^(onsite|manage|teach|learn|volunteer|json)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'program'),
    (r'^(onsite|manage|teach|learn|volunteer|json)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'program'),

    #??? (axiak)
    #(r'^program/Template/$', 'esp.program.views.programTemplateEditor'),
    #(r'^program/(?P<program>[-A-Za-z0-9_ ]+)/(?P<session>[-A-Za-z0-9_ ]+)/Classes/Template/$', 'esp.program.views.classTemplateEditor'),

    # all the archives
    (r'^archives/([-A-Za-z0-9_ ]+)/?$', 'archives'),
    (r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'archives'),
    (r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'archives'),

    # Event-generation
    # Needs to get fixed (axiak)
    #(r'^events/create/$', 'esp.cal.views.createevent'),
    #(r'^events/edit/$', 'esp.cal.views.updateevent'),
    #(r'^events/edit/(?P<id>\d+)/$', 'esp.cal.views.updateevent'),
)

urlpatterns += patterns('',
(r'^(?P<subsection>onsite|manage|teach|learn|volunteer)/(?P<program>[-A-Za-z0-9_ ]+)/?$', RedirectView.as_view(url='/%(subsection)s/%(program)s/index.html')),)

urlpatterns += patterns('', 
    (r'^dataviews/', include('esp.dataviews.urls')) )
    
urlpatterns += patterns('esp.qsdmedia.views', 
    (r'^download\/([^/]+)/?$', 'qsdmedia2'), 
    (r'^download\/([^/]+)\/([^/]+)/?$', 'qsdmedia2') )

urlpatterns += patterns('', 
    (r'^accounting/', include('esp.accounting.urls')) )

urlpatterns += patterns('',
    url(r'^__debug__/', include(debug_toolbar.urls)),
)

urlpatterns += patterns('esp.formstack.views',
    (r'^medicalsyncapi$', 'medicalsyncapi'),)

urlpatterns += patterns('esp.formstack.views',
    (r'^formstack_webhook/?$', 'formstack_webhook'),)

urlpatterns +=patterns('esp.customforms.views',
	(r'^customforms/$','landing'),
	(r'^customforms/create/$','formBuilder'),
	(r'^customforms/submit/$','onSubmit'),
	(r'^customforms/modify/$','onModify'),
	(r'^customforms/view/(?P<form_id>\d{1,6})/$','viewForm'),
	(r'^customforms/success/(?P<form_id>\d{1,6})/$', 'success'),
	(r'^customforms/responses/(?P<form_id>\d{1,6})/$', 'viewResponse'),
	(r'^customforms/getData/$', 'getData'),
	(r'^customforms/metadata/$', 'getRebuildData'),
	(r'^customforms/getperms/$', 'getPerms'),
	(r'^customforms/getlinks/$', 'get_links'),
	(r'^customforms/builddata/$', 'formBuilderData'),
	(r'^customforms/exceldata/(?P<form_id>\d{1,6})/$', 'getExcelData'),
	)	

#   Theme editor
urlpatterns += patterns('', 
                        (r'^themes', include('esp.themes.urls')) 
                       )
