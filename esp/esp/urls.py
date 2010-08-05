__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from django.conf.urls.defaults import patterns, include, handler500, handler404
from django.contrib import admin
from esp.settings import PROJECT_ROOT, MEDIA_ROOT

admin.autodiscover()

from esp.section_data import section_redirect_keys, section_prefix_keys

# Override error pages
handler404 = 'esp.web.util.main.error404'
handler500 = 'esp.web.util.main.error500'

# Static media
urlpatterns = patterns('django.views.static',
                       (r'^media/(?P<path>.*)$', 'serve', {'document_root': MEDIA_ROOT}),
                       (r'^admin/media/(?P<path>.*)$', 'serve', {'document_root': PROJECT_ROOT + 'admin/media/'}),
                       )

# Admin stuff
urlpatterns += patterns('',
                     (r'^admin/ajax_qsd/?', 'esp.qsd.views.ajax_qsd'),
                     (r'^admin/ajax_autocomplete/?', 'esp.db.views.ajax_autocomplete'),
                     (r'^admin/ajax_children/?', 'esp.datatree.views.ajax_children'),
                     (r'^admin/(.*)', admin.site.root),
                     (r'^accounts/login/$', 'esp.users.views.login_checked',),
                     #(r'^learn/Junction/2007_Spring/catalog/?$','django.views.generic.simple.redirect_to', {'url': '/learn/Junction/2007_Summer/catalog/'}),
                     (r'^(?P<subsection>(learn|teach|program|help|manage|onsite))/?$','django.views.generic.simple.redirect_to', {'url': '/%(subsection)s/index.html'} ),
                        )

#   Short term views
urlpatterns += patterns('',
                        (r'^', include('esp.shortterm.urls'),),
                        )


# generic stuff
urlpatterns += patterns('esp.web.views.main',
                        (r'^$', 'home'), # index
                        (r'^web$', 'home'), # index
                        (r'^esp_web', 'home'), # index
                        (r'.php$', 'home'), # index
                        )

# generic stuff
urlpatterns += patterns('django.views.generic',
                        (r'^web/?', 'simple.direct_to_template',{'template':'splash.html'}), # index
                        (r'^web$', 'simple.direct_to_template',{'template':'splash.html'}), # index                        
                        (r'^esp_web', 'simple.direct_to_template',{'template':'splash.html'}), # index
                        (r'.php$', 'simple.direct_to_template',{'template':'splash.html'}), # index                        
                        )

# program stuff
urlpatterns += patterns('',
                        (r'^',  include('esp.program.urls')),
                        )

urlpatterns += patterns('esp.web.views.bio',

                        # bios
                        (r'^(?P<tl>teach|learn)/teachers/(?P<last>[-A-Za-z0-9_ \.]+)/(?P<first>[-A-Za-z_ \.]+)(?P<usernum>[0-9]*)/bio.html$', 'bio'),
                        (r'^(?P<tl>teach|learn)/teachers/(?P<username>[^/]+)/bio.html$', 'bio'),
                        (r'^myesp/teacherbio/?$', 'bio_edit'),
                        (r'^(?P<tl>teach|learn)/teachers/(?P<last>[-A-Za-z0-9_ ]+)/(?P<first>[-A-Za-z_ ]+)(?P<usernum>[0-9]*)/bio.edit.html/?(.*)$', 'bio_edit'),
                        (r'^(?P<tl>teach|learn)/teachers/(?P<username>[^/]+)/bio.edit.html/?(.*)$', 'bio_edit'),
                        )

urlpatterns += patterns('',
                        (r'^myesp/', include('esp.users.urls'),)
                        )

urlpatterns += patterns('',
                        (r'^cache/', include('esp.cache.urls'),)
                        )

urlpatterns += patterns('esp.qsd.views',
                        (r'^(?P<subsection>(learn|teach|programs|manage|onsite))/(?P<url>.*).html$', 'qsd'),
                        (r'^(?P<url>.*)\.html$', 'qsd'),
                        )

#urlpatterns += patterns('',
#                        (r'^(?P<subsection>(learn|teach|programs|manage|onsite))/?$', 'django.views.generic.simple.redirect_to', {'url': '/%(subsection)s/index.html'} ),
#                        )

# logging in and out
urlpatterns += patterns('django.contrib.auth.views',
                     (r'^myesp/signout/?$', 'logout',{'next_page': '/myesp/signedout/'}),
                        )

# other apps
urlpatterns += patterns('',
#                        (r'^alumni/', include('esp.membership.alumni_urls')),
#                        (r'^membership/', include('esp.membership.urls')),
                        (r'^',  include('esp.miniblog.urls')),
                        (r'^',  include('esp.survey.urls')),
                        )

urlpatterns += patterns('esp.web.views.json',

     # JSON
    (r'json/teachers/$', 'teacher_lookup'))

# QSD Media
# aseering 8/14/2007: This ought to be able to be written in a simpler way...
urlpatterns += patterns('esp.web.views.main',

    # Possibly overspecific, possibly too general.
    (r'^(?P<subsection>(learn|teach|program|help))/(?P<url>.*)/qsdmedia/(?P<filename>[^/]+\.[^/]{1,4})$', 'redirect',
        { 'section_redirect_keys': section_redirect_keys, 'renderer': 'esp.qsdmedia.views.qsdmedia', 'section_prefix_keys': section_prefix_keys }),
    (r'^(?P<subsection>(learn|teach|program|help))/qsdmedia/(?P<filename>[^/]+\.[^/]{1,4})$', 'redirect',
        { 'section_redirect_keys': section_redirect_keys, 'renderer': 'esp.qsdmedia.views.qsdmedia', 'section_prefix_keys': section_prefix_keys, 'url': ''}),
    (r'^(?P<url>.*)/qsdmedia/(?P<filename>[^/]+\.[^/]{1,4})$', 'redirect',
        { 'section_redirect_keys': section_redirect_keys, 'renderer': 'esp.qsdmedia.views.qsdmedia' }),
    (r'^qsdmedia/(?P<filename>[^/]+\.[^/]{1,4})$', 'redirect',
        { 'section_redirect_keys': section_redirect_keys, 'renderer': 'esp.qsdmedia.views.qsdmedia', 'url': '' }),

    # aseering - Is it worth consolidating these?  Two entries for the single "contact us! widget
    # Contact Us! pages
    (r'^contact/contact/?$', 'contact'),
    (r'^contact/contact/(?P<section>[^/]+)/?$', 'contact'),
#    (r'^contact/submit.html$', 'contact_submit'),


    # Program stuff
    (r'^(onsite|manage|teach|learn)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'program'),
    (r'^(onsite|manage|teach|learn)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'program'),

    #??? (axiak)
    #(r'^program/Template/$', 'esp.program.views.programTemplateEditor'),
    #(r'^program/(?P<program>[-A-Za-z0-9_ ]+)/(?P<session>[-A-Za-z0-9_ ]+)/Classes/Template/$', 'esp.program.views.classTemplateEditor'),

    # all the archives
    (r'^archives/([-A-Za-z0-9_ ]+)/?$', 'archives'),
    (r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'archives'),
    (r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'archives'),
    (r'^myesp/([-A-Za-z0-9_ ]+)/?$', 'myesp'),

    # DB-generated QSD pages: HTML or plaintext
    #                        (r'^(?P<url>.*)\.html$', 'redirect', { 'section_redirect_keys': section_redirect_keys , 'renderer': qsd} ),
                        )
    
    # Event-generation
    # Needs to get fixed (axiak)
    #(r'^events/create/$', 'esp.cal.views.createevent'),
    #(r'^events/edit/$', 'esp.cal.views.updateevent'),
    #(r'^events/edit/(?P<id>\d+)/$', 'esp.cal.views.updateevent'),

urlpatterns += patterns('esp.web.views.navBar',
    # Update navbar
    (r'^navbar/edit.scm', 'updateNavBar') )
