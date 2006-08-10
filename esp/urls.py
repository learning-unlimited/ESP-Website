from django.conf.urls.defaults import *
from esp.program.models import Class

urlpatterns = patterns('',
    # Example:
    # (r'^esp/', include('esp.apps.foo.urls.foo')),

    # The default
    (r'^$', 'esp.web.views.index'),

    # Generic view for starting a class
    (r'^startaclass/', 'django.views.generic.create_update.create_object', { 'model': Class } ),

    # aseering - Features that are decidedly not done, but are still useable, will end up under "beta/"
    (r'^beta/calendar.ics$', 'esp.web.views.iCalFeed'),

    # aseering - Is it worth consolidating these?  Two entries for the single "contact us! widget
    # Contact Us! pages
    (r'^contact/contact.html$', 'esp.web.views.contact'),
    (r'^contact/submit.html$', 'esp.web.views.contact_submit'),

    (r'^(teach|learn)/teachers/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/bio.html$', 'esp.web.views.bio'),
    (r'^(teach|learn)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'esp.web.views.program'),
    (r'^(teach|learn)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', 'esp.web.views.program'),
    (r'^(learn|teach)/([-A-Za-z0-9/_ ]+)/([-A-Za-z0-9_ ]+).html$', 'esp.web.views.redirect'),
    (r'^myesp/([-A-Za-z0-9_ ]+)/?$', 'esp.web.views.myesp'),

    # Mini-Blog pages
    (r'^blog/(?P<url>.*)/post.scm$', 'esp.miniblog.views.post_miniblog'),
    (r'^blog/(?P<url>.*)/$', 'esp.miniblog.views.show_miniblog'),

    # Event-generation
    (r'^events/create/$', 'esp.calendar.views.createevent'),
    (r'^events/edit/$', 'esp.calendar.views.updateevent'),
    (r'^events/edit/(?P<id>\d+)/$', 'esp.calendar.views.updateevent'),

    # DB-generated QSD pages: HTML or plaintext
    (r'^(?P<url>.*)\.html$', 'esp.qsd.views.qsd'),
    (r'^(?P<url>.*)\.text$', 'esp.qsd.views.qsd_raw'),

    # aseering 8-8-2006: How's this for a definition of a media url?
    # Possibly overspecific, possibly too general.
    (r'^(?P<url>.*)/media/(?P<filename>[^/]+\.[^/]{1,4})$', 'esp.qsdmedia.views.qsdmedia'),

    # Uncomment this for admin:
    (r'^admin/', include('django.contrib.admin.urls')),

    # Uncomment this for @login_required:
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
)
