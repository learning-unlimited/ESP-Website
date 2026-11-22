"""Tests for the URL x role inventory (url_inventory) and crawl_sessions."""

import ast
import csv
import json
import os
import tempfile
import textwrap
from importlib import import_module

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from esp.program.models import ProgramModule
from esp.qsd.models import QuasiStaticData
from esp.tests.factories import make_program, make_user
from esp.users.models import ESPUser
from esp.utils import url_inventory as inv
from esp.utils.management.commands.crawl_sessions import create_user, pick_user


class ExpectedRolesTest(SimpleTestCase):
    def test_needs_admin(self):
        self.assertEqual(inv.expected_roles(['main_call', 'needs_admin']), (['admin'], ''))

    def test_student_view_with_deadline(self):
        roles, note = inv.expected_roles(['needs_student_in_grade', "meets_deadline('/Classes')"])
        self.assertEqual(roles, ['student', 'admin'])
        self.assertEqual(note, '')

    def test_usercheck_usetl_follows_tl(self):
        self.assertEqual(inv.expected_roles(['usercheck_usetl'], tl='teach')[0], ['teacher', 'admin'])

    def test_method_decorator_is_unwrapped(self):
        self.assertEqual(inv.expected_roles(['method_decorator(login_required)'])[0], inv.LOGGED_IN)

    def test_custom_check_has_no_roles(self):
        roles, note = inv.expected_roles(['user_passes_test(test_func)'])
        self.assertIsNone(roles)
        self.assertIn('user_passes_test', note)

    def test_no_access_decorator(self):
        self.assertEqual(inv.expected_roles(['csrf_exempt']), (inv.ROLES, inv.NO_DECORATOR))


class ConcreteUrlTest(SimpleTestCase):
    def test_plain_pattern(self):
        self.assertEqual(inv._concrete_url('^manage/programs/?$', {}), '/manage/programs/')

    def test_named_groups_are_filled(self):
        pattern = r'manage/(?P<program_type>[^/]+)/(?P<program_term>[^/]+)/module_schedule/?$'
        fill = {'program_type': 'Splash', 'program_term': '2026'}
        self.assertEqual(inv._concrete_url(pattern, fill), '/manage/Splash/2026/module_schedule/')

    def test_path_converter_is_filled(self):
        self.assertEqual(inv._concrete_url('forms/<int:form_id>/', {'form_id': '3'}), '/forms/3/')

    def test_alternatives_take_the_first(self):
        self.assertEqual(inv._concrete_url(r'(faq|faq\.html)$', {}), '/faq')

    def test_optional_group_is_dropped(self):
        self.assertEqual(inv._concrete_url('myesp/passwdrecover/(success)?/?$', {}), '/myesp/passwdrecover/')

    def test_unfillable_patterns(self):
        self.assertIsNone(inv._concrete_url('archives/([-A-Za-z0-9_ ]+)/?$', {}))
        self.assertIsNone(inv._concrete_url('contact/(?P<section>[^/]+)/?$', {}))


class WritesOnGetTest(SimpleTestCase):
    def writes(self, source):
        return inv.writes_on_get(ast.parse(textwrap.dedent(source)).body[0])

    def test_unguarded_save(self):
        self.assertEqual(self.writes('''
            def view(self, request):
                obj.save()
        '''), ['obj.save()'])

    def test_post_branch_is_ignored(self):
        self.assertEqual(self.writes('''
            def view(self, request):
                if request.method == 'POST':
                    obj.save()
                return render()
        '''), [])

    def test_else_of_post_check_is_scanned(self):
        self.assertEqual(self.writes('''
            def view(self, request):
                if request.method == 'POST':
                    pass
                else:
                    obj.delete()
        '''), ['obj.delete()'])

    def test_code_after_early_get_return_is_post_only(self):
        self.assertEqual(self.writes('''
            def view(self, request):
                if request.method != 'POST':
                    return render()
                Thing.objects.create(a=1)
        '''), [])

    def test_queryset_update_but_not_dict_update(self):
        self.assertEqual(self.writes('''
            def view(self, request):
                context.update({'a': 1})
                Thing.objects.filter(a=1).update(b=2)
        '''), ['Thing.objects.filter(a=1).update()'])

    def test_nested_blocks_are_scanned(self):
        self.assertEqual(self.writes('''
            def view(self, request):
                for sec in sections:
                    try:
                        sec.unpreregister_student(user)
                    except Exception:
                        pass
        '''), ['sec.unpreregister_student()'])


class UnsafeReasonTest(SimpleTestCase):
    def test_session_ending_views(self):
        self.assertIn('signout', inv._unsafe_reason('/myesp/signout/'))

    def test_writes_make_a_view_unsafe(self):
        self.assertIn('writes_on_get', inv._unsafe_reason('catalog', ['x.save()']))

    def test_reviewed_writes_are_allowed(self):
        self.assertEqual(inv._unsafe_reason('profile', ['x.save()'], 'StudentRegProfileModule.profile'), '')


class InventoryTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.program = make_program(modules=ProgramModule.objects.filter(
            handler__in=['AdminCore', 'TeacherRegCore', 'StudentRegCore']))

    def setUp(self):
        self.rows = inv.build_inventory([self.program])
        self.by_url = {r['url']: r for r in self.rows if r['url']}

    def test_module_views_get_program_urls(self):
        row = self.by_url[f'/manage/{self.program.url}/dashboard']
        self.assertEqual(row['expected_roles'], 'admin')
        self.assertEqual(row['call_type'], 'main')
        self.assertEqual(row['crawlable'], 'yes')

        row = self.by_url[f'/teach/{self.program.url}/teacherreg']
        self.assertEqual(row['expected_roles'], 'teacher, admin')
        self.assertEqual(row['deadline_gated'], 'yes')

    def test_disabled_modules_are_listed_without_a_url(self):
        disabled = ProgramModule.objects.exclude(id__in=self.program.program_modules.all())
        handlers = {f'({pm.handler})' for pm in disabled}
        rows = [r for r in self.rows if r['module'] and r['module'].rsplit(' ', 1)[-1] in handlers]
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row['url'], '')
            self.assertEqual(row['crawlable'], 'no')

    def test_urlconf_views(self):
        self.assertEqual(self.by_url['/manage/programs/']['expected_roles'], 'admin')
        self.assertEqual(self.by_url['/myesp/signout/']['crawlable'], 'no')
        prog_type, prog_term = self.program.url.split('/', 1)
        self.assertIn(f'/manage/{prog_type}/{prog_term}/module_schedule/', self.by_url)

    def test_django_admin_site_expects_admin(self):
        admin_rows = [r for r in self.rows if r['view'].startswith('django.contrib.admin.')]
        self.assertTrue(admin_rows)
        self.assertEqual({r['expected_roles'] for r in admin_rows}, {'admin'})

    def test_urls_are_unique(self):
        urls = [r['url'] for r in self.rows if r['url']]
        self.assertEqual(len(urls), len(set(urls)))

    def test_qsd_pages_are_listed(self):
        author = make_user('Administrator', username='qsd_author')
        QuasiStaticData.objects.create(url='inventory_test_page', title='T', content='C', author=author)
        rows = inv.build_inventory([self.program])
        self.assertIn('/inventory_test_page.html', {r['url'] for r in rows})

    def test_command_writes_csv_and_json(self):
        with tempfile.TemporaryDirectory() as out:
            call_command('url_inventory', program=[self.program.url], out_dir=out, stdout=open(os.devnull, 'w'))
            with open(os.path.join(out, 'inventory.csv'), encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.assertEqual(reader.fieldnames, inv.FIELDS)
                csv_rows = list(reader)
            with open(os.path.join(out, 'inventory.json'), encoding='utf-8') as f:
                data = json.load(f)
        self.assertEqual(data['programs'], [self.program.url])
        self.assertEqual(len(data['rows']), len(csv_rows))


class CrawlSessionsTest(TestCase):
    def setUp(self):
        self.out_dir = tempfile.TemporaryDirectory()
        self.out = os.path.join(self.out_dir.name, 'sessions.json')

    def tearDown(self):
        self.out_dir.cleanup()

    def run_command(self, **kwargs):
        call_command('crawl_sessions', out=self.out, stdout=open(os.devnull, 'w'),
                     stderr=open(os.devnull, 'w'), **kwargs)
        with open(self.out, encoding='utf-8') as f:
            return json.load(f)

    def test_session_logs_the_user_in(self):
        make_user('Teacher', username='crawl_test_teacher')
        data = self.run_command(user=['teacher=crawl_test_teacher'], roles='teacher')
        self.client.cookies[settings.SESSION_COOKIE_NAME] = data['roles']['teacher']['session_key']
        response = self.client.get('/myesp/accountmanage/')
        self.assertEqual(response.wsgi_request.user.username, 'crawl_test_teacher')

    def test_file_is_private(self):
        make_user('Student', username='crawl_test_student')
        self.run_command(user=['student=crawl_test_student'], roles='student')
        self.assertEqual(os.stat(self.out).st_mode & 0o077, 0)

    def test_revoke_deletes_the_sessions(self):
        make_user('Student', username='crawl_test_student')
        key = self.run_command(user=['student=crawl_test_student'], roles='student')['roles']['student']['session_key']
        call_command('crawl_sessions', revoke=self.out, stdout=open(os.devnull, 'w'))
        store = import_module(settings.SESSION_ENGINE).SessionStore()
        self.assertFalse(store.exists(key))

    def test_pick_user_skips_admins_for_other_roles(self):
        admin = make_user('Administrator', username='crawl_test_admin')
        admin.makeRole('Student')
        student = make_user('Student', username='crawl_test_student')
        self.assertEqual(pick_user('student', None), student)

    def test_create_user_makes_an_onsite_user(self):
        program = make_program()
        user = create_user('onsite', program)
        self.assertEqual(user.username, 'crawl_onsite')
        self.assertTrue(ESPUser.objects.get(username='crawl_onsite').isOnsite(program))
