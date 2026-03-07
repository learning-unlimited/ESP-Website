"""
Login rate-limiting middleware using Django's cache backend.

Settings (override in local_settings.py):
    LOGIN_RATELIMIT_MAX_ATTEMPTS  = 5      # failures before lockout
    LOGIN_RATELIMIT_WINDOW        = 900    # tracking window in seconds
    LOGIN_RATELIMIT_LOCKOUT       = 600    # lockout duration in seconds
    LOGIN_RATELIMIT_PATHS         = ['/myesp/login', '/myesp/login/']
    LOGIN_RATELIMIT_TRUSTED_PROXIES = 0   # set >0 to trust X-Forwarded-For
    LOGIN_RATELIMIT_BY_USERNAME   = True  # also track per (IP, username)
"""
import logging
import math
import time

from django.core.cache import cache
from django.conf import settings
from django.shortcuts import render

logger = logging.getLogger(__name__)

# Read configuration once at import time
_MAX_ATTEMPTS      = getattr(settings, 'LOGIN_RATELIMIT_MAX_ATTEMPTS',   5)
_WINDOW            = getattr(settings, 'LOGIN_RATELIMIT_WINDOW',        900)  # 15 min
_LOCKOUT           = getattr(settings, 'LOGIN_RATELIMIT_LOCKOUT',       600)  # 10 min
_LOGIN_PATHS       = getattr(settings, 'LOGIN_RATELIMIT_PATHS',
                             ['/myesp/login', '/myesp/login/'])
_TRUSTED_PROXIES   = getattr(settings, 'LOGIN_RATELIMIT_TRUSTED_PROXIES', 0)
_BY_USERNAME       = getattr(settings, 'LOGIN_RATELIMIT_BY_USERNAME',    True)


# Helpers

def _get_client_ip(request):
    """Return real client IP. Trusts X-Forwarded-For only when TRUSTED_PROXIES > 0."""
    if _TRUSTED_PROXIES > 0:
        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if xff:
            addresses = [a.strip() for a in xff.split(',')]
            index = len(addresses) - _TRUSTED_PROXIES - 1  # skip trusted proxy hops
            if index >= 0:
                return addresses[index]
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _ip_attempt_key(ip):
    return 'rl:ip_attempts:{}'.format(ip)

def _ip_lockout_key(ip):
    return 'rl:ip_lockout:{}'.format(ip)

def _user_attempt_key(ip, username):
    return 'rl:user_attempts:{}:{}'.format(ip, username)

def _user_lockout_key(ip, username):
    return 'rl:user_lockout:{}:{}'.format(ip, username)


def _atomic_increment(key, window):
    """Increment a cache counter atomically using add+incr to avoid race conditions."""
    added = cache.add(key, 1, window)  # no-op if key exists
    if added:
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        # key expired between add() and incr() — retry once
        cache.add(key, 1, window)
        return 1


def _is_locked_out(lockout_key):
    """Return (is_locked: bool, wait_minutes: int). Key stores expiry timestamp."""
    expiry = cache.get(lockout_key)
    if expiry is not None:
        remaining = expiry - time.time()
        if remaining > 0:
            return True, max(1, math.ceil(remaining / 60))
        cache.delete(lockout_key)  # TTL hasn't fired yet; clean up early
    return False, 0


def _apply_lockout(lockout_key, attempts, label):
    """Arm lockout once threshold is reached. cache.add ensures timer is never extended."""
    if attempts >= _MAX_ATTEMPTS:
        expiry_timestamp = time.time() + _LOCKOUT
        armed = cache.add(lockout_key, expiry_timestamp, _LOCKOUT)  # no-op if already locked
        if armed:
            logger.warning(
                'Login rate-limit triggered for %s after %d attempts. Locked for %ds.',
                label, attempts, _LOCKOUT,
            )
            
# Middleware

class LoginRateLimitMiddleware:
    """
    Rate-limits POST requests to the login URL.
    Tracks failures per IP and optionally per (IP, username).
    Clears counters on successful login (HTTP 302).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in _LOGIN_PATHS and request.method == 'POST':
            ip       = _get_client_ip(request)
            username = request.POST.get('username', '').strip()[:150]

            # Check IP lockout
            locked, wait = _is_locked_out(_ip_lockout_key(ip))
            if locked:
                logger.warning('Rate-limited IP %s (%d min remaining)', ip, wait)
                return self._blocked_response(request, wait)

            # Check per-(IP, username) lockout
            if _BY_USERNAME and username:
                locked, wait = _is_locked_out(_user_lockout_key(ip, username))
                if locked:
                    logger.warning('Rate-limited IP %s / user "%s" (%d min remaining)', ip, username, wait)
                    return self._blocked_response(request, wait)

        response = self.get_response(request)

        if request.path in _LOGIN_PATHS and request.method == 'POST':
            ip       = _get_client_ip(request)
            username = request.POST.get('username', '').strip()[:150]

            if response.status_code == 302:
                # Successful login — clear all counters
                cache.delete(_ip_attempt_key(ip))
                cache.delete(_ip_lockout_key(ip))
                if _BY_USERNAME and username:
                    cache.delete(_user_attempt_key(ip, username))
                    cache.delete(_user_lockout_key(ip, username))

            elif response.status_code == 200:
                # Failed login — increment IP counter
                ip_attempts = _atomic_increment(_ip_attempt_key(ip), _WINDOW)
                _apply_lockout(_ip_lockout_key(ip), ip_attempts, 'IP {}'.format(ip))

                # Increment per-(IP, username) counter
                if _BY_USERNAME and username:
                    user_attempts = _atomic_increment(_user_attempt_key(ip, username), _WINDOW)
                    _apply_lockout(_user_lockout_key(ip, username), user_attempts, 'IP {} / user "{}"'.format(ip, username))

        return response

    @staticmethod
    def _blocked_response(request, wait_minutes):
        return render(
            request,
            'registration/login.html',
            {
                'rate_limited':      True,
                'rate_limited_wait': wait_minutes,
            },
            status=429,
        )
