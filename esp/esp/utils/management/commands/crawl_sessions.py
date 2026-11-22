"""
Create logged-in sessions for the browser crawl, one user per role.

    ./manage.py crawl_sessions --program Splash/2026 --out sessions.json
    ./manage.py crawl_sessions --user teacher=jdoe --user admin=asmith ...
    ./manage.py crawl_sessions --revoke sessions.json

Sessions let deploy/release_testing/crawl.py log in as existing users on a
copy of production data without knowing their passwords. The output file
holds live login tokens: keep it private and revoke it after the crawl.
Only run this against a disposable copy of the database.
See docs/dev/release_testing.rst.
"""

import json
import os
from datetime import timedelta
from importlib import import_module

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from esp.program.models import Program, StudentRegistration
from esp.program.models.class_ import ClassSubject
from esp.users.models import ESPUser, Permission

LOGIN_ROLES = ['student', 'teacher', 'volunteer', 'onsite', 'admin']
ROLE_GROUPS = {'student': 'Student', 'teacher': 'Teacher', 'volunteer': 'Volunteer', 'admin': 'Administrator'}


def pick_user(role, program):
    """An active user for a role, preferring one involved in the program.

    Non-admin roles skip admins, since admins pass every access check.
    """
    users = ESPUser.objects.filter(is_active=True)
    if role != 'admin':
        users = users.exclude(groups__name='Administrator')
    preferred = ESPUser.objects.none()
    if role == 'admin':
        users = users.filter(groups__name='Administrator')
    elif role == 'onsite':
        users = users.filter(permission__permission_type='Onsite')
        if program is not None:
            preferred = users.filter(permission__program=program)
    else:
        users = users.filter(groups__name=ROLE_GROUPS[role])
        if program is not None and role == 'teacher':
            preferred = users.filter(classsubject__in=ClassSubject.objects.filter(parent_program=program))
        elif program is not None and role == 'student':
            preferred = users.filter(studentregistration__in=StudentRegistration.valid_objects().filter(
                section__parent_class__parent_program=program))
        elif program is not None and role == 'volunteer':
            preferred = users.filter(volunteeroffer__request__program=program)
    return preferred.order_by('id').first() or users.order_by('id').first()


def create_user(role, program):
    """A new crawl_<role> user with that role (used with --create-missing)."""
    user, _ = ESPUser.objects.get_or_create(
        username=f'crawl_{role}',
        defaults={'first_name': 'Crawl', 'last_name': role.title(), 'email': f'crawl_{role}@example.com'})
    user.set_unusable_password()
    user.is_active = True
    user.save()
    if role == 'onsite':
        Permission.objects.get_or_create(user=user, permission_type='Onsite', program=program)
    elif role == 'admin':
        user.makeAdmin()
    else:
        user.makeRole(ROLE_GROUPS[role])
    return user


def make_session(user, hours):
    store = import_module(settings.SESSION_ENGINE).SessionStore()
    store[SESSION_KEY] = user._meta.pk.value_to_string(user)
    store[BACKEND_SESSION_KEY] = settings.AUTHENTICATION_BACKENDS[0]
    store[HASH_SESSION_KEY] = user.get_session_auth_hash()
    store.set_expiry(int(hours * 3600))
    store.create()
    return store.session_key


class Command(BaseCommand):
    help = 'Create login sessions for the browser crawl (disposable databases only)'

    def add_arguments(self, parser):
        parser.add_argument('--program', metavar='URL',
                            help='Prefer users involved in this program, e.g. Splash/2026.')
        parser.add_argument('--user', action='append', default=[], metavar='ROLE=USERNAME',
                            help=f'Use this user for a role. Roles: {", ".join(LOGIN_ROLES)}.')
        parser.add_argument('--roles', default=','.join(LOGIN_ROLES),
                            help='Comma-separated roles to create sessions for.')
        parser.add_argument('--create-missing', action='store_true',
                            help='Create a crawl_<role> user for any role with no suitable user. '
                                 'Writes to the database.')
        parser.add_argument('--hours', type=float, default=4,
                            help='How long the sessions last (default 4).')
        parser.add_argument('--out', default='sessions.json',
                            help='File to write the sessions to.')
        parser.add_argument('--revoke', metavar='FILE',
                            help='Delete the sessions listed in FILE and exit.')

    def handle(self, *args, **options):
        engine = import_module(settings.SESSION_ENGINE)
        if options['revoke']:
            with open(options['revoke'], encoding='utf-8') as f:
                data = json.load(f)
            for role, info in data['roles'].items():
                engine.SessionStore(session_key=info['session_key']).delete()
            self.stdout.write(f'Revoked {len(data["roles"])} sessions from {options["revoke"]}')
            return

        program = None
        if options['program']:
            program = Program.objects.filter(url=options['program']).first()
            if program is None:
                raise CommandError(f'No program with URL {options["program"]!r}')

        chosen = {}
        for spec in options['user']:
            role, _, username = spec.partition('=')
            if role not in LOGIN_ROLES or not username:
                raise CommandError(f'Bad --user {spec!r}; expected ROLE=USERNAME with ROLE in {LOGIN_ROLES}')
            user = ESPUser.objects.filter(username=username).first()
            if user is None:
                raise CommandError(f'No user named {username!r}')
            chosen[role] = user

        roles = [r.strip() for r in options['roles'].split(',') if r.strip()]
        result = {
            'cookie_name': settings.SESSION_COOKIE_NAME,
            'expires_at': (timezone.now() + timedelta(hours=options['hours'])).isoformat(),
            'program': program.url if program else None,
            'roles': {},
        }
        for role in roles:
            if role not in LOGIN_ROLES:
                raise CommandError(f'Unknown role {role!r}')
            user = chosen.get(role) or pick_user(role, program)
            if user is None and options['create_missing']:
                user = create_user(role, program)
            if user is None:
                self.stderr.write(f'No user found for role {role!r}; skipping it '
                                  '(use --user or --create-missing)')
                continue
            result['roles'][role] = {'username': user.username, 'session_key': make_session(user, options['hours'])}
            self.stdout.write(f'{role:10} {user.username}')

        # Owner-only permissions: the file holds login tokens
        fd = os.open(options['out'], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=1)
        self.stdout.write(f'Wrote {options["out"]}. It contains login tokens: '
                          f'revoke with --revoke {options["out"]} when done.')
