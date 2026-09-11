"""
Tests for the transport-security settings added alongside SecurityMiddleware.

The DEBUG-dependent settings (secure cookies, SSL redirect, HSTS) are derived
in esp/settings.py rather than esp/django_settings.py, because
django_settings.py defaults DEBUG to False and local_settings.py -- which
supplies the real value -- is imported afterwards.  Deriving them in
django_settings.py would enable production-only hardening in development.
These tests pin that behaviour so the settings cannot drift back.

Note on the DEBUG reference value: these tests deliberately do NOT compare
against settings.DEBUG.  pytest-django forces settings.DEBUG to False for the
duration of the run (its django_debug_mode ini option), so at test time it no
longer reflects how the site is configured.  The derivation in settings.py
consumes the value local_settings.py supplies, so that is what the expected
values are computed from here.
"""
import unittest

from django.conf import settings

from esp import django_settings, local_settings


# The DEBUG value the derivation in esp/settings.py actually saw: whatever
# local_settings.py set, falling back to django_settings.py's default.
CONFIGURED_DEBUG = getattr(local_settings, 'DEBUG', django_settings.DEBUG)

DERIVED_FROM_DEBUG = (
    'SESSION_COOKIE_SECURE',
    'CSRF_COOKIE_SECURE',
    'SECURE_SSL_REDIRECT',
)


class SecuritySettingsTest(unittest.TestCase):
    def test_security_middleware_runs_first(self):
        """
        SecurityMiddleware must be the outermost middleware so that its SSL
        redirect and HSTS header apply to every response, including those
        short-circuited by middleware further down the stack.
        """
        self.assertEqual(settings.MIDDLEWARE[0],
                         'django.middleware.security.SecurityMiddleware')

    def test_debug_derived_flags_follow_configured_debug(self):
        """
        Each flag must track the configured DEBUG.  Before these settings were
        moved out of django_settings.py they evaluated `not DEBUG` against that
        module's own DEBUG = False default, so they were True even in a
        DEBUG = True checkout -- which redirects the development server to
        HTTPS and stops session and CSRF cookies from being sent over plain
        HTTP.
        """
        for name in DERIVED_FROM_DEBUG:
            if hasattr(local_settings, name):
                # This deployment overrides the derived value on purpose.
                continue
            with self.subTest(setting=name):
                self.assertEqual(getattr(settings, name), not CONFIGURED_DEBUG)

    def test_hsts_not_enabled_in_debug(self):
        """
        HSTS cannot be revoked before it expires, so it must stay off in
        development -- a stray HSTS header on localhost pins every other local
        project on that host to HTTPS for the lifetime of the max-age.
        """
        if hasattr(local_settings, 'SECURE_HSTS_SECONDS'):
            self.skipTest('SECURE_HSTS_SECONDS overridden in local_settings')
        if CONFIGURED_DEBUG:
            self.assertEqual(settings.SECURE_HSTS_SECONDS, 0)
        else:
            self.assertGreater(settings.SECURE_HSTS_SECONDS, 0)

    def test_hsts_scope_expanders_are_opt_in(self):
        """
        includeSubDomains affects sibling subdomains and preload is effectively
        irreversible, so neither may be on by default; deployments opt in via
        local_settings.py.
        """
        for name in ('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'SECURE_HSTS_PRELOAD'):
            if hasattr(local_settings, name):
                continue
            with self.subTest(setting=name):
                self.assertFalse(getattr(settings, name))

    def test_no_global_proxy_ssl_header(self):
        """
        SECURE_PROXY_SSL_HEADER makes Django trust a client-controllable header
        unless the proxy strips it.  The reference Apache + mod_wsgi deployment
        has no such proxy, so this must not be a global default; deployments
        behind a TLS terminator set it in local_settings.py.
        """
        if hasattr(local_settings, 'SECURE_PROXY_SSL_HEADER'):
            self.skipTest('SECURE_PROXY_SSL_HEADER set in local_settings')
        self.assertIsNone(settings.SECURE_PROXY_SSL_HEADER)

    def test_csrf_cookie_readable_by_javascript(self):
        """
        csrf_init.js and csrf_check.js read settings.CSRF_COOKIE_NAME via
        $.cookie() to populate csrfmiddlewaretoken fields and X-CSRFToken
        headers.  Setting HttpOnly would break every AJAX POST until that JS
        is migrated to a server-rendered token.
        """
        self.assertFalse(settings.CSRF_COOKIE_HTTPONLY)
