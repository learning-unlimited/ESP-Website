
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
from django.conf.urls.defaults import *
from esp.program.models import Class
from esp.qsd.views import qsd
from esp.poll.views import poll
from esp.qsdmedia.views import qsdmedia


#	This is some lookup for the redirector, to insert a certain string for the tree node 
section_redirect_keys = {'teach': 'Programs',
                         'learn': 'Programs',
                         'program': 'Programs',
                         'help': 'ESP/Committees',
                         None: 'Web'}

section_prefix_keys = {'teach': 'teach', 'learn': 'learn'}

# Patterns outside of esp.web.views...
urlpatterns_list =  [(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/esp/esp/media/'}),
                     (r'^admin/media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/esp/esp/admin/media/'}),
                     # Uncomment this for admin:
                     (r'^admin/', include('django.contrib.admin.urls')),
                     # Uncomment this for @login_required:
                     (r'^accounts/login/$', 'django.contrib.auth.views.login'),

                     
                     # Mini-Blog pages
                     # These are broken...must fix (axiak)
                     #(r'^(?P<subsection>teach|learn|help)/(?P<url>.*)/blog/$', 'esp.miniblog.views.show_miniblog', {'section_redirect_keys': section_redirect_keys}),
                     (r'^blog/(?P<url>.*)/post/$', 'esp.miniblog.views.post_miniblog'),
                     (r'^blog/(?P<url>.*)/$', 'esp.miniblog.views.show_miniblog_entry'),
                     (r'^blog/$', 'esp.miniblog.views.show_miniblog', {'url': '', 'section_redirect_keys': section_redirect_keys}),


                    ]

# All of these *must* reside in esp.web.views
esppatterns_list = [
    # Example:
    # (r'^esp/', include('esp.apps.foo.urls.foo')),

    # Possibly overspecific, possibly too general.
    (r'^(?P<subsection>(learn|teach|program|help))/(?P<url>.*)/media/(?P<filename>[^/]+\.[^/]{1,4})$', 'redirect',
        { 'section_redirect_keys': section_redirect_keys, 'renderer': qsdmedia, 'section_prefix_keys': section_prefix_keys }),
    
    (r'^(?P<url>.*)/media/(?P<filename>[^/]+\.[^/]{1,4})$', 'redirect',
        { 'section_redirect_keys': section_redirect_keys, 'renderer': qsdmedia }),

    # Main page
    (r'^$', 'index'),
    
    # backwards compatibility...
    (r'^web/index\.html$', 'index'),

    # JSON
    (r'json/teachers/$', 'teacher_lookup'),

    # aseering - Is it worth consolidating these?  Two entries for the single "contact us! widget
    # Contact Us! pages
    (r'^contact/contact/?$', 'contact'),
    (r'^contact/contact/(?P<section>[^/]+)/?$', 'contact'),
    (r'^contact/submit.html$', 'contact_submit'),


    # bios
    (r'^(teach|learn)/teachers/([-A-Za-z0-9_ ]+)/([-A-Za-z_ ]+)([0-9]*)/bio.html$', 'bio'),
    (r'^(teach|learn)/teachers/([-A-Za-z0-9_ ]+)/([-A-Za-z_ ]+)([0-9]*)/bio.edit.html/?(.*)$', 'bio_edit'),

    # Program stuff
    (r'^(onsite|manage|teach|learn)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'program'),
    (r'^(onsite|manage|teach|learn)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'program'),
    (r'^onsite/home/?', 'program'),

    #??? (axiak)
    #(r'^program/Template/$', 'esp.program.views.programTemplateEditor'),
    #(r'^program/(?P<program>[-A-Za-z0-9_ ]+)/(?P<session>[-A-Za-z0-9_ ]+)/Classes/Template/$', 'esp.program.views.classTemplateEditor'),

    # all the archives
    (r'^archives/([-A-Za-z0-9_ ]+)/?$', 'archives'),
    (r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'archives'),
    (r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'archives'),

    
    (r'^(?P<subsection>(learn|teach|program|help))/(?P<url>.*).html$', 'redirect',
        { 'section_redirect_keys': section_redirect_keys, 'section_prefix_keys': section_prefix_keys } ),
	
    # myESP Page
    (r'^myesp/([-A-Za-z0-9_ ]+)/?$', 'myesp'),

    # Event-generation
    # Needs to get fixed (axiak)
    #(r'^events/create/$', 'esp.cal.views.createevent'),
    #(r'^events/edit/$', 'esp.cal.views.updateevent'),
    #(r'^events/edit/(?P<id>\d+)/$', 'esp.cal.views.updateevent'),

    # DB-generated QSD pages: HTML or plaintext
    (r'^(?P<url>.*)\.html$', 'redirect', { 'section_redirect_keys': section_redirect_keys , 'renderer': qsd} ),
    (r'^(?P<url>.*)\.poll$', 'redirect', { 'section_redirect_keys': section_redirect_keys , 'renderer': poll} ),

    # Update navbar
    (r'^navbar/edit.scm', 'updateNavBar'),

    # Reimbursement requests
    # Needs to be better
    #(r'^money/reimbursement/$', 'esp.money.views.create_reimbursement'),

    # Redirect
    (r'^(?P<temp>.*).php$', 'simple_redirect', {'target': 'http://esp.mit/edu/missing_page.html'}),
    (r'^esp_web(?P<temp>.*)$', 'simple_redirect', {'target': 'http://esp.mit.edu/missing_page.html'}),
    ]



# Now we turn what was above into a neat little urlpatterns for Django
root = 'esp.web.views.everything.'
for i in range(len(esppatterns_list)):
    # Since tuples are immutable...
    if len(esppatterns_list[i]) == 2:
        esppatterns_list[i] = (esppatterns_list[i][0],
                               root + esppatterns_list[i][1],)
    elif len(esppatterns_list[i]) == 3:
        esppatterns_list[i] = (esppatterns_list[i][0],
                               root + esppatterns_list[i][1],
                               esppatterns_list[i][2],)
                            

urlpatterns_list = urlpatterns_list + esppatterns_list

urlpatterns = patterns('', *urlpatterns_list)


