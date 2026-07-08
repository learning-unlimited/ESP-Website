from __future__ import absolute_import
import six
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

import json
import re
from unittest import mock

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.qsd.models import QuasiStaticData, QSDConflict, edit_history, version_snapshot
from esp.qsd.forms import QSDMoveForm, QSDBulkMoveForm
from esp.web.models import NavBarCategory, default_navbarcategory
from esp.users.models import ESPUser, Permission
from esp.program.models import Program
from esp.tagdict.models import Tag

from django.db import transaction
from django.db.utils import IntegrityError
from django.template import Template, Context
from reversion import revisions as reversion


def extract_hidden_value(html, name):
    """ Pulls a hidden <input>'s value out of rendered HTML, for tests that
    need to round-trip the orig_id/orig_version fields through a real form
    submission. """
    match = re.search(r'name="%s" value="([^"]*)"' % re.escape(name), html)
    return match.group(1) if match else None


def extract_data_attr(html, name):
    """ Pulls a data-* attribute's value out of rendered HTML, for tests that
    need the orig_id/orig_version tokens embedded in an inline QSD block's
    rendered container. """
    match = re.search(r'data-%s="([^"]*)"' % re.escape(name), html)
    return match.group(1) if match else None

class QSDCorrectnessTest(TestCase):
    """ Tests to ensure that QSD-related caches are cleared appropriately. """

    def setUp(self):
        #   Determine URL for QSD page to be tested
        section = 'learn'
        pagename = 'foo'
        self.url = '/%s/%s.html' % (section, pagename)

        #   Create user to function as QSD author
        new_admin, created = ESPUser.objects.get_or_create(username='qsd_admin')
        new_admin.set_password('password')
        new_admin.save()
        new_admin.makeRole('Administrator')
        new_student, created = ESPUser.objects.get_or_create(username='qsd_student')
        new_student.set_password('password')
        new_student.save()
        self.users = [None, (new_admin, 'password'), (new_student, 'password')]
        self.author = new_admin

    def testInlineCorrectness(self):

        for user in self.users:
            if user is None:
                self.client.logout()
            else:
                self.client.logout()
                self.client.login(username=user[0], password=user[1])

            #   Create an inline QSD
            qsd_rec_new = QuasiStaticData()
            qsd_rec_new.url = 'learn/bar'
            qsd_rec_new.name = "learn:bar"
            qsd_rec_new.author = self.author
            qsd_rec_new.nav_category = default_navbarcategory()
            qsd_rec_new.content = "Inline Testing 123"
            qsd_rec_new.title = "Test QSD page"
            qsd_rec_new.description = ""
            qsd_rec_new.keywords = ""
            qsd_rec_new.save()

            #   Render a template that uses the inline_qsd template tag
            template_data = """
                {% load render_qsd %}
                {% render_inline_qsd "learn/bar" %}
            """
            template = Template(template_data)
            response_content = template.render(Context({}))
            self.assertTrue("Inline Testing 123" in response_content)

            #   Update the template and check again
            qsd_rec_new.content = "Inline Testing 456"
            qsd_rec_new.save()
            response_content = template.render(Context({}))
            self.assertTrue("Inline Testing 456" in response_content)

            response_content = template.render(Context({}))
            self.assertTrue("Inline Testing 456" in response_content)

            #   Delete it so we can start again
            qsd_rec_new.delete()

    def testPageCorrectness(self):

        for user in self.users:
            if user is None:
                self.client.logout()
            else:
                self.client.logout()
                self.client.login(username=user[0], password=user[1])

            #   Check that QSD with desired URL does not exist
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 404)

            #   Create QSD with desired URL
            qsd_rec_new = QuasiStaticData()
            qsd_rec_new.url = 'learn/foo'
            qsd_rec_new.name = "learn:foo"
            qsd_rec_new.author = self.author
            qsd_rec_new.nav_category = default_navbarcategory()
            qsd_rec_new.content = "Testing 123"
            qsd_rec_new.title = "Test QSD page"
            qsd_rec_new.description = ""
            qsd_rec_new.keywords = ""
            qsd_rec_new.save()

            #   Check that page now exists and has proper content
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue('Testing 123' in six.text_type(response.content, encoding='UTF-8'))

            #   Edit QSD and check that page content has updated
            qsd_rec_new.content = "Testing 456"
            qsd_rec_new.save()
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue('Testing 456' in six.text_type(response.content, encoding='UTF-8'))

            #   Delete the new QSD so we can start again.
            qsd_rec_new.delete()


class QSDDisabledTest(TestCase):
    """ Tests for how the disabled flag affects full-page and inline QSDs. """

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='qsd_disabled_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')
        self.client.login(username='qsd_disabled_admin', password='password')

    def tearDown(self):
        QuasiStaticData.objects.filter(url__startswith='qsddisabledtest').delete()

    def make_page(self, url, content, disabled=False):
        qsd = QuasiStaticData()
        qsd.url = url
        qsd.author = self.admin
        qsd.nav_category = default_navbarcategory()
        qsd.content = content
        qsd.title = 'Test page'
        qsd.description = ''
        qsd.keywords = ''
        qsd.disabled = disabled
        qsd.save()
        return qsd

    def test_disabled_page_404s_for_reader(self):
        self.make_page('qsddisabledtest/page', 'live content')
        response = self.client.get('/qsddisabledtest/page.html')
        self.assertEqual(response.status_code, 200)

        qsd = QuasiStaticData.objects.get(url='qsddisabledtest/page')
        qsd.disabled = True
        qsd.save()

        response = self.client.get('/qsddisabledtest/page.html')
        self.assertEqual(response.status_code, 404)

    def test_disabled_page_shows_create_prompt_for_editor(self):
        self.make_page('qsddisabledtest/page2', 'live content', disabled=True)
        response = self.client.get('/qsddisabledtest/page2.html')
        self.assertEqual(response.status_code, 404)
        self.assertIn('Page does not exist', response.content.decode('utf-8'))

    def test_editing_disabled_page_reuses_and_reenables_same_row(self):
        qsd = self.make_page('qsddisabledtest/page3', 'old disabled content', disabled=True)
        original_pk = qsd.pk

        response = self.client.get('/qsddisabledtest/page3.edit.html')
        html = response.content.decode('utf-8')
        # Should start from the blank/default placeholder, not the old
        # disabled content.
        self.assertNotIn('old disabled content', html)
        self.assertIn('Please insert your text here', html)
        orig_id = extract_hidden_value(html, 'orig_id')
        orig_version = extract_hidden_value(html, 'orig_version')
        self.assertEqual(orig_id, str(original_pk))

        self.client.post('/qsddisabledtest/page3.edit.html', {
            'post_edit': '1',
            'title': 'Revived page',
            'keywords': '',
            'description': '',
            'nav_category': default_navbarcategory().id,
            'content': 'new content',
            'orig_id': orig_id,
            'orig_version': orig_version or '',
        })

        qsd.refresh_from_db()
        self.assertEqual(qsd.pk, original_pk)  # same row reused, not a new one
        self.assertFalse(qsd.disabled)
        self.assertEqual(qsd.content, 'new content')

    def test_inline_render_of_disabled_block_falls_back_to_default(self):
        self.make_page('qsddisabledtest/inline0', 'old disabled inline content', disabled=True)
        template_data = """
            {% load render_qsd %}
            {% render_inline_qsd "qsddisabledtest/inline0" %}
        """
        rendered = Template(template_data).render(Context({}))
        self.assertNotIn('old disabled inline content', rendered)

    def test_editing_disabled_inline_block_reenables_it(self):
        qsd = self.make_page('qsddisabledtest/inline1', 'old disabled inline content', disabled=True)
        original_pk = qsd.pk

        response = self.client.post('/admin/ajax_qsd', {
            'cmd': 'update',
            'url': 'qsddisabledtest/inline1',
            'data': 'revived inline content',
            'orig_id': str(original_pk),
            'orig_version': '',
        }, HTTP_REFERER='/qsddisabledtest/somepage.html')
        self.assertEqual(response.status_code, 200)

        qsd.refresh_from_db()
        self.assertEqual(qsd.pk, original_pk)
        self.assertFalse(qsd.disabled)
        self.assertEqual(qsd.content, 'revived inline content')


class QSDUniqueUrlTest(TestCase):
    """ QuasiStaticData.url must be unique at the DB level. """

    def test_duplicate_url_raises_integrity_error(self):
        admin, _ = ESPUser.objects.get_or_create(username='qsd_unique_admin')
        QuasiStaticData.objects.filter(url='qsdtest/uniqueurl').delete()

        first = QuasiStaticData(url='qsdtest/uniqueurl', author=admin,
                                 nav_category=default_navbarcategory(),
                                 content='a', title='a', description='', keywords='')
        first.save()

        second = QuasiStaticData(url='qsdtest/uniqueurl', author=admin,
                                  nav_category=default_navbarcategory(),
                                  content='b', title='b', description='', keywords='')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                second.save()

        QuasiStaticData.objects.filter(url='qsdtest/uniqueurl').delete()


class QSDConflictTest(TestCase):
    """
    Tests for optimistic-concurrency conflict detection on QSD edits: the
    "someone else changed this since you started editing" protection added
    to qsd() and ajax_qsd() via QuasiStaticData.objects.save_with_conflict_check.
    """

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='qsd_conflict_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')
        self.client.login(username='qsd_conflict_admin', password='password')
        self.nav_category = default_navbarcategory()

    def tearDown(self):
        QuasiStaticData.objects.filter(url__startswith='qsdconflicttest').delete()

    def get_edit_form(self, url):
        response = self.client.get('/' + url + '.edit.html')
        html = response.content.decode('utf-8')
        return {
            'orig_id': extract_hidden_value(html, 'orig_id') or '',
            'orig_version': extract_hidden_value(html, 'orig_version') or '',
        }

    def post_edit(self, url, content, orig_id, orig_version, title='Test', follow=False):
        return self.client.post('/' + url + '.edit.html', {
            'post_edit': '1',
            'title': title,
            'keywords': '',
            'description': '',
            'nav_category': self.nav_category.id,
            'content': content,
            'orig_id': orig_id,
            'orig_version': orig_version,
        }, follow=follow)

    def test_sequential_edits_succeed_and_reuse_same_row(self):
        url = 'qsdconflicttest/page1'
        tokens = self.get_edit_form(url)
        self.post_edit(url, 'v1', **tokens)
        qsd = QuasiStaticData.objects.get(url=url)
        first_pk = qsd.pk

        tokens = self.get_edit_form(url)
        self.assertEqual(tokens['orig_id'], str(first_pk))
        self.post_edit(url, 'v2', **tokens)

        qsd.refresh_from_db()
        self.assertEqual(qsd.pk, first_pk)
        self.assertEqual(qsd.content, 'v2')

    def test_edit_after_save_does_not_conflict_with_itself(self):
        """
        Regression test: a successful post_edit() must not embed a stale
        orig_version in the response it leaves the client with, or the
        client's *next* save (based on that response) would spuriously
        conflict with the edit it just made itself. This specifically
        exercises the response the POST itself resolves to (following any
        redirect), not a separate fresh GET -- a separate GET would land
        outside the just-completed request's revision context and wouldn't
        catch this class of bug.
        """
        url = 'qsdconflicttest/page6'
        tokens = self.get_edit_form(url)
        self.post_edit(url, 'v1', **tokens)

        response = self.post_edit(url, 'v2', follow=True, **self.get_edit_form(url))
        html = response.content.decode('utf-8')
        self.assertNotIn('changed by someone else', html)
        next_tokens = {
            'orig_id': extract_hidden_value(html, 'orig_id') or '',
            'orig_version': extract_hidden_value(html, 'orig_version') or '',
        }

        response = self.post_edit(url, 'v3', **next_tokens)
        html = response.content.decode('utf-8')
        self.assertNotIn('changed by someone else', html)
        self.assertEqual(QuasiStaticData.objects.get(url=url).content, 'v3')

    def test_stale_edit_shows_conflict_and_preserves_submission(self):
        url = 'qsdconflicttest/page2'
        tokens = self.get_edit_form(url)
        self.post_edit(url, 'v1', **tokens)

        # Load the edit form (capturing the *stale* tokens), then someone
        # else saves a change before we submit.
        stale_tokens = self.get_edit_form(url)
        other_tokens = self.get_edit_form(url)
        self.post_edit(url, 'v2-by-someone-else', **other_tokens)

        response = self.post_edit(url, 'my-unsaved-edit', **stale_tokens)
        html = response.content.decode('utf-8')
        self.assertIn('changed by someone else', html)
        # Our attempted content is preserved in the redisplayed form, not lost.
        self.assertIn('my-unsaved-edit', html)

        qsd = QuasiStaticData.objects.get(url=url)
        self.assertEqual(qsd.content, 'v2-by-someone-else')  # not clobbered

    def test_conflict_page_lists_recent_editor(self):
        url = 'qsdconflicttest/page3'
        tokens = self.get_edit_form(url)
        self.post_edit(url, 'v1', **tokens)

        stale_tokens = self.get_edit_form(url)
        other_tokens = self.get_edit_form(url)
        self.post_edit(url, 'v2', **other_tokens)

        response = self.post_edit(url, 'my-edit', **stale_tokens)
        html = response.content.decode('utf-8')
        self.assertIn(self.admin.username, html)

    def test_deleted_page_conflict(self):
        url = 'qsdconflicttest/page4'
        tokens = self.get_edit_form(url)
        self.post_edit(url, 'v1', **tokens)

        stale_tokens = self.get_edit_form(url)
        QuasiStaticData.objects.filter(url=url).delete()

        response = self.post_edit(url, 'my-edit', **stale_tokens)
        self.assertIn('changed by someone else', response.content.decode('utf-8'))
        self.assertFalse(QuasiStaticData.objects.filter(url=url).exists())

    def test_deleted_and_recreated_conflict(self):
        url = 'qsdconflicttest/page5'
        tokens = self.get_edit_form(url)
        self.post_edit(url, 'v1', **tokens)
        original_pk = QuasiStaticData.objects.get(url=url).pk

        stale_tokens = self.get_edit_form(url)
        QuasiStaticData.objects.filter(url=url).delete()
        recreate_tokens = self.get_edit_form(url)
        self.post_edit(url, 'v2-recreated', **recreate_tokens)
        recreated_pk = QuasiStaticData.objects.get(url=url).pk
        self.assertNotEqual(original_pk, recreated_pk)

        response = self.post_edit(url, 'my-stale-edit', **stale_tokens)
        self.assertIn('changed by someone else', response.content.decode('utf-8'))
        self.assertEqual(QuasiStaticData.objects.get(url=url).content, 'v2-recreated')

    def test_ajax_qsd_conflict_returns_409(self):
        url = 'qsdconflicttest/inline1'
        qsd = QuasiStaticData(url=url, author=self.admin, nav_category=self.nav_category,
                               content='v1', title='t', description='', keywords='')
        qsd.save()

        response = self.client.post('/admin/ajax_qsd', {
            'cmd': 'update', 'url': url, 'data': 'v2',
            'orig_id': str(qsd.pk), 'orig_version': '',
        }, HTTP_REFERER='/qsdconflicttest/somepage.html')
        self.assertEqual(response.status_code, 200)

        # Stale resubmission reusing the *original* (now outdated) tokens
        # should conflict, since the row was just updated above.
        response = self.client.post('/admin/ajax_qsd', {
            'cmd': 'update', 'url': url, 'data': 'v3-stale',
            'orig_id': str(qsd.pk), 'orig_version': '',
        }, HTTP_REFERER='/qsdconflicttest/somepage.html')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(QuasiStaticData.objects.get(url=url).content, 'v2')

        # The conflict response carries refreshed orig_id/orig_version, so a
        # deliberate resubmit using them is treated as a real override, not
        # another stale attempt.
        payload = json.loads(response.content.decode('utf-8'))
        current = QuasiStaticData.objects.get(url=url)
        self.assertEqual(payload['orig_id'], current.pk)
        response = self.client.post('/admin/ajax_qsd', {
            'cmd': 'update', 'url': url, 'data': 'v4-deliberate-override',
            'orig_id': str(payload['orig_id']), 'orig_version': str(payload['orig_version']),
        }, HTTP_REFERER='/qsdconflicttest/somepage.html')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(QuasiStaticData.objects.get(url=url).content, 'v4-deliberate-override')

    def test_subsequent_inline_edits_do_not_conflict_with_themselves(self):
        """
        Mirrors test_edit_after_save_does_not_conflict_with_itself, for the
        ajax inline-editing path. The inline editor never gets its
        orig_id/orig_version from the ajax response itself -- it comes from
        whatever page most recently rendered the block (the
        data-orig-id/-version attributes on #inline_edit_<id>). The existing
        JS does a full page reload after every successful save specifically
        to pick up a fresh render before allowing another edit. This
        re-renders the containing template after each save (standing in for
        that reload) to get the next edit's tokens, and confirms three
        edits in a row against the same block never spuriously conflict.
        """
        url = 'qsdconflicttest/inline2'
        template = Template("""
            {% load render_qsd %}
            {% render_inline_qsd "qsdconflicttest/inline2" %}
        """)

        def render_tokens():
            html = template.render(Context({}))
            return {
                'orig_id': extract_data_attr(html, 'orig-id') or '',
                'orig_version': extract_data_attr(html, 'orig-version') or '',
            }

        def save(content):
            payload = {'cmd': 'update', 'url': url, 'data': content}
            payload.update(render_tokens())
            return self.client.post('/admin/ajax_qsd', payload,
                                     HTTP_REFERER='/qsdconflicttest/somepage.html')

        for content in ('v1', 'v2', 'v3'):
            response = save(content)
            self.assertEqual(response.status_code, 200)

        self.assertEqual(QuasiStaticData.objects.get(url=url).content, 'v3')


class QSDManagePagesTest(TestCase):
    """ Tests for the /manage/pages delete/undelete/move actions. """

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='qsd_managepages_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')
        self.client.login(username='qsd_managepages_admin', password='password')
        self.nav_category = default_navbarcategory()

    def tearDown(self):
        QuasiStaticData.objects.filter(url__startswith='qsdmanagepagestest').delete()

    def make_page(self, url):
        qsd = QuasiStaticData(url=url, author=self.admin, nav_category=self.nav_category,
                               content='c', title='t', description='', keywords='')
        qsd.save()
        return qsd

    def test_delete_disables_page(self):
        qsd = self.make_page('qsdmanagepagestest/page1')
        self.client.post('/manage/pages?cmd=delete&id=%d' % qsd.pk, {'sure': 'True'})
        qsd.refresh_from_db()
        self.assertTrue(qsd.disabled)

    def test_undelete_reenables_page(self):
        qsd = self.make_page('qsdmanagepagestest/page2')
        qsd.disabled = True
        qsd.save()
        self.client.get('/manage/pages?cmd=undelete&id=%d' % qsd.pk)
        qsd.refresh_from_db()
        self.assertFalse(qsd.disabled)

    def test_move_updates_url(self):
        qsd = self.make_page('qsdmanagepagestest/page3')
        self.client.post('/manage/pages?cmd=move&id=%d' % qsd.pk, {
            'id': qsd.pk,
            'destination': 'qsdmanagepagestest/page3moved',
            'nav_category': self.nav_category.id,
        })
        qsd.refresh_from_db()
        self.assertEqual(qsd.url, 'qsdmanagepagestest/page3moved')

    def test_bulk_move_updates_urls(self):
        qsd1 = self.make_page('qsdmanagepagestest/bulk/a')
        qsd2 = self.make_page('qsdmanagepagestest/bulk/b')
        self.client.post('/manage/pages?cmd=bulk_move', {
            'confirm': '1',
            'id_list': '%d,%d' % (qsd1.pk, qsd2.pk),
            'destination': 'qsdmanagepagestest/movedbulk',
        })
        qsd1.refresh_from_db()
        qsd2.refresh_from_db()
        self.assertEqual(qsd1.url, 'qsdmanagepagestest/movedbulk/a')
        self.assertEqual(qsd2.url, 'qsdmanagepagestest/movedbulk/b')


class QSDStalenessCheckTest(TestCase):
    """
    Tests for proactively warning an editor that their starting point is
    already out of date -- before they invest time editing -- rather than
    only discovering it when they try to save.

    NOT YET IMPLEMENTED. An inline block's orig_id/orig_version come from
    whatever page last rendered it (data-orig-id/-version), which may itself
    be a stale/cached render -- unlike the full-page editor, where a GET to
    <url>.edit.html always queries fresh, so there's nothing to proactively
    warn about there. These inline tests are expected to fail until
    ajax_qsd grows a side-effect-free cmd='check_fresh' action; the
    full-page test is a confirming (already-passing) test showing that gap
    doesn't exist on that path.
    """

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='qsd_staleness_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')
        self.client.login(username='qsd_staleness_admin', password='password')
        self.nav_category = default_navbarcategory()

    def tearDown(self):
        QuasiStaticData.objects.filter(url__startswith='qsdstalenesstest').delete()

    def check_fresh(self, url, orig_id, orig_version):
        return self.client.post('/admin/ajax_qsd', {
            'cmd': 'check_fresh',
            'url': url,
            'orig_id': orig_id,
            'orig_version': orig_version,
        }, HTTP_REFERER='/qsdstalenesstest/somepage.html')

    def test_check_fresh_reports_stale_for_outdated_inline_tokens(self):
        url = 'qsdstalenesstest/inline1'
        qsd = QuasiStaticData(url=url, author=self.admin, nav_category=self.nav_category,
                               content='v1', title='t', description='', keywords='')
        qsd.save()
        # These are "what the editor started from" -- captured before
        # anyone else's edit below.
        orig_id, orig_version = str(qsd.pk), ''

        # Someone else edits the block before our (hypothetical) editor
        # gets around to saving.
        self.client.post('/admin/ajax_qsd', {
            'cmd': 'update', 'url': url, 'data': 'v2-by-someone-else',
            'orig_id': orig_id, 'orig_version': orig_version,
        }, HTTP_REFERER='/qsdstalenesstest/somepage.html')

        response = self.check_fresh(url, orig_id, orig_version)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertTrue(result['stale'])
        self.assertTrue(result['history'])
        self.assertEqual(result['content'], 'v2-by-someone-else')

    def test_check_fresh_reports_current_content_even_when_tokens_are_not_stale(self):
        """
        Guards against a real browser quirk: browsers can restore a
        <textarea>'s old value across a plain page refresh even when the
        server sent fresh default content, while the container div's
        data-orig-id/-version attributes (not form controls) are unaffected
        and come through fresh. check_freshness's token comparison alone
        can't see this -- the client additionally compares the actual
        current content (returned here) against what's really in the
        textarea, so 'content' must always be present, stale or not.
        """
        url = 'qsdstalenesstest/inline1b'
        qsd = QuasiStaticData(url=url, author=self.admin, nav_category=self.nav_category,
                               content='current-content', title='t', description='', keywords='')
        qsd.save()

        version = qsd.latest_version_id()
        response = self.check_fresh(url, str(qsd.pk), str(version) if version is not None else '')
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertFalse(result['stale'])
        self.assertEqual(result['content'], 'current-content')

    def test_check_fresh_reports_not_stale_for_current_inline_tokens(self):
        url = 'qsdstalenesstest/inline2'
        qsd = QuasiStaticData(url=url, author=self.admin, nav_category=self.nav_category,
                               content='v1', title='t', description='', keywords='')
        qsd.save()

        response = self.check_fresh(url, str(qsd.pk), '')
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content.decode('utf-8'))
        self.assertFalse(result['stale'])

    def test_full_page_edit_form_already_reflects_current_state_on_open(self):
        """ Confirming test, not expected to fail: opening the full-page
        editor always shows the true current state, so there's no
        "already stale before you start" gap on this path. """
        url = 'qsdstalenesstest/page1'
        qsd = QuasiStaticData(url=url, author=self.admin, nav_category=self.nav_category,
                               content='v1', title='t', description='', keywords='')
        qsd.save()

        # Someone else edits the page.
        other = QuasiStaticData.objects.get(url=url)
        other.content = 'v2-by-someone-else'
        other.save()

        response = self.client.get('/' + url + '.edit.html')
        html = response.content.decode('utf-8')
        self.assertEqual(extract_hidden_value(html, 'orig_id'), str(qsd.pk))
        self.assertIn('v2-by-someone-else', html)


class QSDTemplateTagTest(TestCase):
    """ Tests for esp/qsd/templatetags/render_qsd.py paths not covered by
    QSDCorrectnessTest, which only exercises the simpler render_inline_qsd()
    function tag: the inline_qsd_block/inline_program_qsd_block block tags
    (InlineQSDNode) that real templates like the homepage and the teacher
    waiver page actually use, render_qsd_md, the qsd_display_date_author
    Date/None branches, and the prog_qsd_url/program_from_url round trip. """

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='qsd_templatetag_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')
        self.nav_category = default_navbarcategory()
        self.program, _ = Program.objects.get_or_create(
            url='Templatetagtest/2026', defaults={
                'name': 'Template Tag Test Program', 'grade_min': 7,
                'grade_max': 12, 'director_email': 'esp@mit.edu',
                'program_size_max': 100})

    def tearDown(self):
        Tag.unSetTag('qsd_display_date_author')
        QuasiStaticData.objects.filter(url__startswith='qsdtemplatetagtest').delete()
        QuasiStaticData.objects.filter(url__startswith='teach/Templatetagtest').delete()

    def test_inline_qsd_block_renders_default_content_when_no_row_exists(self):
        template = Template(
            '{% load render_qsd %}'
            '{% inline_qsd_block "qsdtemplatetagtest/block1" %}'
            'Block default content'
            '{% end_inline_qsd_block %}'
        )
        rendered = template.render(Context({}))
        self.assertIn('Block default content', rendered)
        # InlineQSDNode never saves -- it only synthesizes a default row for
        # display, so nothing should exist in the DB until someone edits it.
        self.assertFalse(QuasiStaticData.objects.filter(url='qsdtemplatetagtest/block1').exists())

    def test_inline_qsd_block_renders_saved_content_when_row_exists(self):
        QuasiStaticData.objects.create(
            url='qsdtemplatetagtest/block2', name='', title='t',
            content='Saved block content', author=self.admin,
            nav_category=self.nav_category, description='', keywords='')
        template = Template(
            '{% load render_qsd %}'
            '{% inline_qsd_block "qsdtemplatetagtest/block2" %}'
            'Default content, still available via Load'
            '{% end_inline_qsd_block %}'
        )
        rendered = template.render(Context({}))
        self.assertIn('Saved block content', rendered)
        # The block tag's own default content is exposed separately (in a
        # hidden qsd_default_content_ textarea, for the inline editor's
        # "load the default content" option) but must not be what's shown
        # or what the editable textarea starts from.
        self.assertIn('Default content, still available via Load', rendered)
        edit_textarea = re.search(r'name="qsd_content">([^<]*)</textarea>', rendered).group(1)
        self.assertEqual(edit_textarea, 'Saved block content')

    def test_inline_program_qsd_block_computes_program_scoped_url_and_renders_default(self):
        template = Template(
            '{% load render_qsd %}'
            '{% inline_program_qsd_block prog "teach:instructions" %}'
            'Default instructions'
            '{% end_inline_program_qsd_block %}'
        )
        rendered = template.render(Context({'prog': self.program}))
        self.assertIn('Default instructions', rendered)
        expected_url = QuasiStaticData.prog_qsd_url(self.program, 'teach:instructions')
        self.assertEqual(expected_url, 'teach/Templatetagtest/2026/instructions')
        self.assertFalse(QuasiStaticData.objects.filter(url=expected_url).exists())

    def test_inline_program_qsd_block_renders_saved_content_when_row_exists(self):
        url = QuasiStaticData.prog_qsd_url(self.program, 'teach:instructions')
        QuasiStaticData.objects.create(
            url=url, name='', title='t', content='Saved instructions',
            author=self.admin, nav_category=self.nav_category,
            description='', keywords='')
        template = Template(
            '{% load render_qsd %}'
            '{% inline_program_qsd_block prog "teach:instructions" %}'
            'Default instructions, still available via Load'
            '{% end_inline_program_qsd_block %}'
        )
        rendered = template.render(Context({'prog': self.program}))
        self.assertIn('Saved instructions', rendered)
        # The block tag's own default content is exposed separately (in a
        # hidden qsd_default_content_ textarea, for the inline editor's
        # "load the default content" option) but must not be what's shown
        # or what the editable textarea starts from.
        self.assertIn('Default instructions, still available via Load', rendered)
        edit_textarea = re.search(r'name="qsd_content">([^<]*)</textarea>', rendered).group(1)
        self.assertEqual(edit_textarea, 'Saved instructions')

    def test_prog_qsd_url_and_program_from_url_round_trip_with_prefix(self):
        url = QuasiStaticData.prog_qsd_url(self.program, 'teach:waiver_instructions')
        self.assertEqual(url, 'teach/Templatetagtest/2026/waiver_instructions')
        prog, name = QuasiStaticData.program_from_url(url)
        self.assertEqual(prog, self.program)
        self.assertEqual(name, 'teach:waiver_instructions')

    def test_prog_qsd_url_and_program_from_url_round_trip_without_prefix(self):
        url = QuasiStaticData.prog_qsd_url(self.program, 'somepage')
        self.assertEqual(url, 'programs/Templatetagtest/2026/somepage')
        prog, name = QuasiStaticData.program_from_url(url)
        self.assertEqual(prog, self.program)
        self.assertEqual(name, 'somepage')

    def test_program_from_url_returns_none_for_unrelated_url(self):
        self.assertIsNone(QuasiStaticData.program_from_url('learn/some/unrelated/page'))

    def test_render_qsd_md_tag_renders_markdown_content(self):
        qsd = QuasiStaticData.objects.create(
            url='qsdtemplatetagtest/mdpage', name='', title='t',
            content='**bold markdown content**', author=self.admin,
            nav_category=self.nav_category, description='', keywords='')
        template = Template('{% load render_qsd %}{% render_qsd_md qsdrec %}')
        rendered = template.render(Context({'qsdrec': qsd}))
        self.assertIn('<strong>bold markdown content</strong>', rendered)

    def test_render_qsd_display_date_author_date_only(self):
        Tag.setTag('qsd_display_date_author', value='Date')
        qsd = QuasiStaticData.objects.create(
            url='qsdtemplatetagtest/datepage', name='', title='t',
            content='content', author=self.admin,
            nav_category=self.nav_category, description='', keywords='')
        template = Template('{% load render_qsd %}{% render_qsd qsdrec %}')
        rendered = template.render(Context({'qsdrec': qsd}))
        # Date-only: the "by <author>" phrase is individually hidden, but the
        # surrounding date/author div itself is not.
        self.assertIn('<span class="qsd_bits hidden">by', rendered)
        self.assertNotIn('class="qsd_bits hidden" id="divmainqsddatetimestamp"', rendered)

    def test_render_qsd_display_date_author_none(self):
        Tag.setTag('qsd_display_date_author', value='None')
        qsd = QuasiStaticData.objects.create(
            url='qsdtemplatetagtest/nodatepage', name='', title='t',
            content='content', author=self.admin,
            nav_category=self.nav_category, description='', keywords='')
        template = Template('{% load render_qsd %}{% render_qsd qsdrec %}')
        rendered = template.render(Context({'qsdrec': qsd}))
        # None: the whole date/author div is hidden, with no separate span.
        self.assertIn('class="qsd_bits hidden" id="divmainqsddatetimestamp"', rendered)
        self.assertNotIn('<span class="qsd_bits hidden">by', rendered)

    def test_render_qsd_md_display_date_author_date_only(self):
        Tag.setTag('qsd_display_date_author', value='Date')
        qsd = QuasiStaticData.objects.create(
            url='qsdtemplatetagtest/mddatepage', name='', title='t',
            content='content', author=self.admin,
            nav_category=self.nav_category, description='', keywords='')
        template = Template('{% load render_qsd %}{% render_qsd_md qsdrec %}')
        rendered = template.render(Context({'qsdrec': qsd}))
        self.assertIn('<span class="qsd_bits hidden">by', rendered)
        self.assertNotIn('class="qsd_bits hidden" id="divmainqsddatetimestamp"', rendered)

    def test_render_qsd_md_display_date_author_none(self):
        Tag.setTag('qsd_display_date_author', value='None')
        qsd = QuasiStaticData.objects.create(
            url='qsdtemplatetagtest/mdnodatepage', name='', title='t',
            content='content', author=self.admin,
            nav_category=self.nav_category, description='', keywords='')
        template = Template('{% load render_qsd %}{% render_qsd_md qsdrec %}')
        rendered = template.render(Context({'qsdrec': qsd}))
        self.assertIn('class="qsd_bits hidden" id="divmainqsddatetimestamp"', rendered)
        self.assertNotIn('<span class="qsd_bits hidden">by', rendered)

    def test_render_inline_program_qsd_function_tag(self):
        template = Template(
            '{% load render_qsd %}'
            '{% render_inline_program_qsd prog "teach:instructions" %}'
        )
        rendered = template.render(Context({'prog': self.program}))
        expected_url = QuasiStaticData.prog_qsd_url(self.program, 'teach:instructions')
        self.assertEqual(expected_url, 'teach/Templatetagtest/2026/instructions')
        self.assertIn('placeholder for editable text', rendered)

    def test_inline_program_qsd_block_falls_back_when_program_variable_missing(self):
        """ If the program template variable doesn't resolve (e.g. a typo, or
        used outside the context it's meant for), InlineQSDNode should treat
        it as if no program was given, rather than raising. """
        template = Template(
            '{% load render_qsd %}'
            '{% inline_program_qsd_block does_not_exist "qsdtemplatetagtest/block3" %}'
            'Default content'
            '{% end_inline_program_qsd_block %}'
        )
        rendered = template.render(Context({}))
        self.assertIn('Default content', rendered)

    def test_inline_qsd_block_rejects_wrong_number_of_arguments(self):
        with self.assertRaises(Exception):
            Template(
                '{% load render_qsd %}'
                '{% inline_qsd_block %}'
                'content'
                '{% end_inline_qsd_block %}'
            )

    def test_inline_program_qsd_block_rejects_wrong_number_of_arguments(self):
        with self.assertRaises(Exception):
            Template(
                '{% load render_qsd %}'
                '{% inline_program_qsd_block prog %}'
                'content'
                '{% end_inline_program_qsd_block %}'
            )


class QSDHistoryRevertTest(TestCase):
    """
    Tests for the version-history page/panel and revert-to-a-past-version
    feature: the 'history' action + post_revert handling in qsd() (full
    page), and the 'history'/'preview_version'/'revert' commands in
    ajax_qsd() (inline editor).
    """

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='qsd_history_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')
        self.client.login(username='qsd_history_admin', password='password')
        self.nav_category = default_navbarcategory()

    def tearDown(self):
        QuasiStaticData.objects.filter(url__startswith='qsdhistorytest').delete()

    def get_edit_form(self, url):
        response = self.client.get('/' + url + '.edit.html')
        html = response.content.decode('utf-8')
        return {
            'orig_id': extract_hidden_value(html, 'orig_id') or '',
            'orig_version': extract_hidden_value(html, 'orig_version') or '',
        }

    def post_edit(self, url, content, orig_id, orig_version, title='Test', follow=False):
        return self.client.post('/' + url + '.edit.html', {
            'post_edit': '1',
            'title': title,
            'keywords': '',
            'description': '',
            'nav_category': self.nav_category.id,
            'content': content,
            'orig_id': orig_id,
            'orig_version': orig_version,
        }, follow=follow)

    def post_revert(self, url, version_id, orig_id, orig_version):
        return self.client.post('/' + url + '.history.html', {
            'post_revert': '1',
            'version_id': version_id,
            'orig_id': orig_id,
            'orig_version': orig_version,
        })

    def version_ids(self, url):
        """ [version_id, ...] for url's history, most recent first. """
        qsd = QuasiStaticData.objects.get(url=url)
        return [h['version_id'] for h in edit_history(qsd, limit=None)]

    def test_history_page_lists_all_versions_most_recent_first(self):
        url = 'qsdhistorytest/page1'
        self.post_edit(url, 'v1', **self.get_edit_form(url))
        self.post_edit(url, 'v2', **self.get_edit_form(url))

        response = self.client.get('/' + url + '.history.html')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertEqual(html.count('(current version)'), 1)
        self.assertEqual(html.count('Preview</a>'), 1)

    def test_history_404s_for_nonexistent_page(self):
        response = self.client.get('/qsdhistorytest/doesnotexist.history.html')
        self.assertEqual(response.status_code, 404)

    def test_history_requires_edit_permission(self):
        url = 'qsdhistorytest/page2'
        self.post_edit(url, 'v1', **self.get_edit_form(url))
        self.client.logout()
        response = self.client.get('/' + url + '.history.html')
        self.assertEqual(response.status_code, 403)

    def test_preview_shows_version_content_without_reverting(self):
        url = 'qsdhistorytest/page3'
        self.post_edit(url, 'v1-unique', **self.get_edit_form(url))
        self.post_edit(url, 'v2-unique', **self.get_edit_form(url))

        latest_id, older_id = self.version_ids(url)
        response = self.client.get('/' + url + '.history.html?preview=%s' % older_id)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn('v1-unique', html)
        self.assertIn('Revert to this version', html)

        # Merely previewing must not touch the saved content.
        self.assertEqual(QuasiStaticData.objects.get(url=url).content, 'v2-unique')

    def test_preview_404s_for_unknown_version_id(self):
        url = 'qsdhistorytest/page4'
        self.post_edit(url, 'v1', **self.get_edit_form(url))
        response = self.client.get('/' + url + '.history.html?preview=999999')
        self.assertEqual(response.status_code, 404)

    def test_revert_restores_content_and_appends_a_forward_version(self):
        url = 'qsdhistorytest/page5'
        self.post_edit(url, 'v1', **self.get_edit_form(url), title='Title1')
        self.post_edit(url, 'v2', **self.get_edit_form(url), title='Title2')
        self.post_edit(url, 'v3', **self.get_edit_form(url), title='Title3')

        versions_before = self.version_ids(url)
        self.assertEqual(len(versions_before), 3)
        v1_id = versions_before[-1]  # oldest

        history_tokens = self.get_edit_form(url)  # orig_id/orig_version work the same for both forms
        response = self.post_revert(url, v1_id, history_tokens['orig_id'], history_tokens['orig_version'])
        self.assertEqual(response.status_code, 302)

        qsd = QuasiStaticData.objects.get(url=url)
        self.assertEqual(qsd.content, 'v1')
        self.assertEqual(qsd.title, 'Title1')

        # The revert itself is a new forward version, not a rewrite of history.
        versions_after = self.version_ids(url)
        self.assertEqual(len(versions_after), 4)

    def test_revert_rejects_version_id_belonging_to_a_different_page(self):
        url_a = 'qsdhistorytest/page6a'
        url_b = 'qsdhistorytest/page6b'
        self.post_edit(url_a, 'a1', **self.get_edit_form(url_a))
        self.post_edit(url_b, 'b1', **self.get_edit_form(url_b))

        [b_version_id] = self.version_ids(url_b)
        tokens = self.get_edit_form(url_a)
        response = self.post_revert(url_a, b_version_id, tokens['orig_id'], tokens['orig_version'])
        self.assertEqual(response.status_code, 404)
        self.assertEqual(QuasiStaticData.objects.get(url=url_a).content, 'a1')

    def test_revert_conflict_does_not_apply_and_shows_banner(self):
        url = 'qsdhistorytest/page7'
        self.post_edit(url, 'v1', **self.get_edit_form(url))
        self.post_edit(url, 'v2', **self.get_edit_form(url))

        v2_id, v1_id = self.version_ids(url)
        stale_tokens = self.get_edit_form(url)

        # Someone else edits the page after we loaded the history page.
        self.post_edit(url, 'v3-by-someone-else', **self.get_edit_form(url))

        response = self.post_revert(url, v1_id, stale_tokens['orig_id'], stale_tokens['orig_version'])
        self.assertEqual(response.status_code, 200)
        self.assertIn('changed by someone else', response.content.decode('utf-8'))
        self.assertEqual(QuasiStaticData.objects.get(url=url).content, 'v3-by-someone-else')

    def test_ajax_history_lists_versions_most_recent_first(self):
        url = 'qsdhistorytest/inline1'
        referer = {'HTTP_REFERER': '/qsdhistorytest/somepage.html'}
        self.client.post('/admin/ajax_qsd', {'cmd': 'update', 'url': url, 'data': 'v1',
                                              'orig_id': '', 'orig_version': ''}, **referer)
        qsd = QuasiStaticData.objects.get(url=url)
        self.client.post('/admin/ajax_qsd', {'cmd': 'update', 'url': url, 'data': 'v2',
                                              'orig_id': str(qsd.pk),
                                              'orig_version': str(qsd.latest_version_id())}, **referer)

        response = self.client.post('/admin/ajax_qsd', {'cmd': 'history', 'url': url}, **referer)
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(payload['history']), 2)
        self.assertTrue(all('version_id' in h and 'user' in h and 'date' in h for h in payload['history']))

    def test_ajax_preview_version_renders_without_saving(self):
        url = 'qsdhistorytest/inline2'
        referer = {'HTTP_REFERER': '/qsdhistorytest/somepage.html'}
        self.client.post('/admin/ajax_qsd', {'cmd': 'update', 'url': url, 'data': 'v1-unique',
                                              'orig_id': '', 'orig_version': ''}, **referer)
        qsd = QuasiStaticData.objects.get(url=url)
        self.client.post('/admin/ajax_qsd', {'cmd': 'update', 'url': url, 'data': 'v2-unique',
                                              'orig_id': str(qsd.pk),
                                              'orig_version': str(qsd.latest_version_id())}, **referer)

        history = json.loads(self.client.post(
            '/admin/ajax_qsd', {'cmd': 'history', 'url': url}, **referer).content.decode('utf-8'))['history']
        v1_id = history[-1]['version_id']

        response = self.client.post('/admin/ajax_qsd', {'cmd': 'preview_version', 'url': url,
                                                          'version_id': v1_id}, **referer)
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode('utf-8'))
        self.assertIn('v1-unique', payload['content'])
        self.assertEqual(QuasiStaticData.objects.get(url=url).content, 'v2-unique')

    def test_ajax_preview_version_404s_for_unknown_version(self):
        url = 'qsdhistorytest/inline3'
        referer = {'HTTP_REFERER': '/qsdhistorytest/somepage.html'}
        self.client.post('/admin/ajax_qsd', {'cmd': 'update', 'url': url, 'data': 'v1',
                                              'orig_id': '', 'orig_version': ''}, **referer)

        response = self.client.post('/admin/ajax_qsd', {'cmd': 'preview_version', 'url': url,
                                                          'version_id': '999999'}, **referer)
        self.assertEqual(response.status_code, 404)

    def test_ajax_preview_version_returns_raw_content_not_rendered_html(self):
        """
        preview_version returns the raw stored content (not markdown-
        rendered HTML) -- the inline editor loads it straight into the
        textarea/rich-text widget for the user to review and possibly save
        (a "revert" is just loading an old version and clicking the
        ordinary Save button), so it needs the actual editable source, not
        a display rendering of it.
        """
        url = 'qsdhistorytest/inline4'
        referer = {'HTTP_REFERER': '/qsdhistorytest/somepage.html'}
        self.client.post('/admin/ajax_qsd', {'cmd': 'update', 'url': url, 'data': '# v1-heading',
                                              'orig_id': '', 'orig_version': ''}, **referer)
        qsd = QuasiStaticData.objects.get(url=url)
        self.client.post('/admin/ajax_qsd', {'cmd': 'update', 'url': url, 'data': 'v2',
                                              'orig_id': str(qsd.pk),
                                              'orig_version': str(qsd.latest_version_id())}, **referer)

        history = json.loads(self.client.post(
            '/admin/ajax_qsd', {'cmd': 'history', 'url': url}, **referer).content.decode('utf-8'))['history']
        v1_id = history[-1]['version_id']

        response = self.client.post('/admin/ajax_qsd', {'cmd': 'preview_version', 'url': url,
                                                          'version_id': v1_id}, **referer)
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode('utf-8'))
        self.assertEqual(payload['content'], '# v1-heading')


class QSDModelCoverageTest(TestCase):
    """ Coverage-gap tests for esp/esp/qsd/models.py: edit_history's limit
    cutoff, version_snapshot's None-object guards, the genuine DB-race
    IntegrityError branch in save_with_conflict_check (simulated via mock,
    since a real concurrent race can't be reliably forced inside a single
    test transaction), QSDManager.__repr__/__str__, QuasiStaticData.copy(),
    and get_absolute_url(). """

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='qsd_modelcoverage_admin')
        self.nav_category = default_navbarcategory()

    def tearDown(self):
        QuasiStaticData.objects.filter(url__startswith='qsdmodelstest').delete()

    def test_edit_history_stops_at_default_limit(self):
        url = 'qsdmodelstest/historylimit'
        qsd = QuasiStaticData(url=url, author=self.admin, nav_category=self.nav_category,
                               content='v0', title='t', description='', keywords='')
        with reversion.create_revision():
            qsd.save()
        for i in range(1, 7):
            with reversion.create_revision():
                qsd.content = 'v%d' % i
                qsd.save()

        history = edit_history(qsd)
        self.assertEqual(len(history), 5)

    def test_edit_history_full_when_limit_is_none(self):
        url = 'qsdmodelstest/historyfull'
        qsd = QuasiStaticData(url=url, author=self.admin, nav_category=self.nav_category,
                               content='v0', title='t', description='', keywords='')
        with reversion.create_revision():
            qsd.save()
        for i in range(1, 7):
            with reversion.create_revision():
                qsd.content = 'v%d' % i
                qsd.save()

        history = edit_history(qsd, limit=None)
        self.assertEqual(len(history), 7)

    def test_version_snapshot_returns_none_for_none_object(self):
        self.assertIsNone(version_snapshot(None, 1))

    def test_version_snapshot_returns_none_for_unsaved_object(self):
        unsaved = QuasiStaticData(url='qsdmodelstest/unsaved', author=self.admin,
                                   nav_category=self.nav_category, content='c', title='t',
                                   description='', keywords='')
        self.assertIsNone(version_snapshot(unsaved, 1))

    def test_save_with_conflict_check_converts_integrity_error_to_conflict(self):
        """
        Simulates the genuine DB-race branch (two requests both creating a
        brand-new url) by forcing save() to raise IntegrityError directly,
        since reliably triggering the real race requires actual concurrent
        transactions.
        """
        url = 'qsdmodelstest/raceurl'

        def populate(rec):
            rec.title = 't'
            rec.content = 'c'
            rec.description = ''
            rec.keywords = ''
            rec.nav_category = self.nav_category
            rec.author = self.admin

        with mock.patch.object(QuasiStaticData, 'save', side_effect=IntegrityError('duplicate key')):
            with self.assertRaises(QSDConflict):
                QuasiStaticData.objects.save_with_conflict_check(url, None, None, populate)

        self.assertFalse(QuasiStaticData.objects.filter(url=url).exists())

    def test_manager_repr_and_str(self):
        self.assertEqual(repr(QuasiStaticData.objects), "QSDManager()")
        self.assertEqual(str(QuasiStaticData.objects), "QSDManager()")

    def test_copy_returns_unsaved_duplicate_with_same_fields(self):
        qsd = QuasiStaticData.objects.create(
            url='qsdmodelstest/copysrc', author=self.admin, nav_category=self.nav_category,
            content='c', title='t', description='d', keywords='k')

        duplicate = qsd.copy()

        self.assertIsNone(duplicate.pk)
        self.assertEqual(duplicate.url, qsd.url)
        self.assertEqual(duplicate.author, qsd.author)
        self.assertEqual(duplicate.content, qsd.content)
        self.assertEqual(duplicate.title, qsd.title)
        self.assertEqual(duplicate.description, qsd.description)
        self.assertEqual(duplicate.nav_category, qsd.nav_category)
        self.assertEqual(duplicate.keywords, qsd.keywords)
        self.assertEqual(duplicate.disabled, qsd.disabled)
        self.assertEqual(duplicate.create_date, qsd.create_date)

    def test_get_absolute_url(self):
        qsd = QuasiStaticData(url='qsdmodelstest/absurl')
        self.assertEqual(qsd.get_absolute_url(), '/qsdmodelstest/absurl.html')


class QSDFormsCoverageTest(TestCase):
    """ Coverage-gap tests for esp/esp/qsd/forms.py: QSDMoveForm.load_data
    and both branches of QSDBulkMoveForm.load_data (shared-prefix found vs.
    not found). """

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='qsd_formscoverage_admin')
        self.nav_category = default_navbarcategory()

    def tearDown(self):
        QuasiStaticData.objects.filter(url__startswith='qsdformstest').delete()

    def test_move_form_load_data_populates_initial_fields(self):
        qsd = QuasiStaticData.objects.create(
            url='qsdformstest/page1', author=self.admin, nav_category=self.nav_category,
            content='c', title='t', description='', keywords='')

        form = QSDMoveForm()
        form.load_data(qsd)

        self.assertEqual(form.fields['id'].initial, qsd.id)
        self.assertEqual(form.fields['destination'].initial, qsd.url)
        self.assertEqual(form.fields['nav_category'].initial, qsd.nav_category)

    def test_bulk_move_form_load_data_returns_common_path_when_shared(self):
        qsd1 = QuasiStaticData.objects.create(
            url='qsdformstest/bulk/a', author=self.admin, nav_category=self.nav_category,
            content='c', title='t', description='', keywords='')
        qsd2 = QuasiStaticData.objects.create(
            url='qsdformstest/bulk/b', author=self.admin, nav_category=self.nav_category,
            content='c', title='t', description='', keywords='')

        form = QSDBulkMoveForm()
        result = form.load_data([qsd1, qsd2])

        self.assertEqual(result, 'qsdformstest/bulk')
        self.assertEqual(form.fields['id_list'].initial, '%d,%d' % (qsd1.id, qsd2.id))
        self.assertEqual(form.fields['destination'].initial, 'qsdformstest/bulk')

    def test_bulk_move_form_load_data_returns_false_when_no_shared_path(self):
        form = QSDBulkMoveForm()
        self.assertFalse(form.load_data([]))


class QSDViewsCoverageTest(TestCase):
    """
    Coverage-gap tests for esp/esp/qsd/views.py: permission-denied branches
    across qsd()/ajax_qsd(), the create-action alias, the no-op-edit
    (diff_found False) fallthrough, the class_qsd HTML-sanitizing branch,
    the invalid ?preview= param, the unexpected-action 404, ajax_qsd's
    anonymous-session/unknown-cmd branches, and ajax_qsd_preview (previously
    entirely untested).
    """

    def setUp(self):
        self.admin, _ = ESPUser.objects.get_or_create(username='qsd_viewscoverage_admin')
        self.admin.set_password('password')
        self.admin.save()
        self.admin.makeRole('Administrator')
        self.nonadmin, _ = ESPUser.objects.get_or_create(username='qsd_viewscoverage_nonadmin')
        self.nonadmin.set_password('password')
        self.nonadmin.save()
        self.nav_category = default_navbarcategory()

    def tearDown(self):
        QuasiStaticData.objects.filter(url__startswith='qsdcoveragetest').delete()
        self.client.logout()

    def make_page(self, url, content='content', title='Test page'):
        qsd = QuasiStaticData(url=url, author=self.admin, nav_category=self.nav_category,
                               content=content, title=title, description='', keywords='')
        qsd.save()
        return qsd

    def login_admin(self):
        self.client.login(username='qsd_viewscoverage_admin', password='password')

    def login_nonadmin(self):
        self.client.login(username='qsd_viewscoverage_nonadmin', password='password')

    def test_read_of_manage_section_forbidden_for_non_admin(self):
        self.client.logout()
        response = self.client.get('/manage/qsdcoveragetest/somepage.html')
        self.assertEqual(response.status_code, 403)

    def test_edit_of_nonexistent_page_forbidden_without_edit_permission(self):
        self.client.logout()
        response = self.client.get('/qsdcoveragetest/nonexistent.edit.html')
        self.assertEqual(response.status_code, 403)

    def test_create_action_on_existing_page_behaves_like_edit(self):
        self.make_page('qsdcoveragetest/createaction')
        self.login_admin()
        response = self.client.get('/qsdcoveragetest/createaction.create.html')
        self.assertEqual(response.status_code, 200)

    def test_post_edit_forbidden_without_edit_permission(self):
        self.make_page('qsdcoveragetest/noeditperm')
        self.login_nonadmin()
        response = self.client.post('/qsdcoveragetest/noeditperm.edit.html', {
            'post_edit': '1', 'title': 't', 'keywords': '', 'description': '',
            'nav_category': self.nav_category.id, 'content': 'new', 'orig_id': '', 'orig_version': '',
        })
        self.assertEqual(response.status_code, 403)

    def test_post_edit_sanitizes_class_qsd_content(self):
        url = 'manage/Prog/2026/Classes/coveragepage'
        self.make_page(url, content='old')
        self.login_admin()
        response = self.client.get('/' + url + '.edit.html')
        html = response.content.decode('utf-8')
        orig_id = extract_hidden_value(html, 'orig_id') or ''
        orig_version = extract_hidden_value(html, 'orig_version') or ''

        self.client.post('/' + url + '.edit.html', {
            'post_edit': '1', 'title': 't', 'keywords': '', 'description': '',
            'nav_category': self.nav_category.id,
            'content': '<script>alert(1)</script>Hello',
            'orig_id': orig_id, 'orig_version': orig_version,
        })

        saved = QuasiStaticData.objects.get(url=url)
        self.assertNotIn('<script>', saved.content)
        self.assertIn('Hello', saved.content)

    def test_post_edit_with_no_changes_is_a_no_op(self):
        qsd = self.make_page('qsdcoveragetest/noop', content='same content', title='Same title')
        self.login_admin()
        response = self.client.post('/qsdcoveragetest/noop.edit.html', {
            'post_edit': '1', 'title': 'Same title', 'keywords': '', 'description': '',
            'nav_category': self.nav_category.id, 'content': 'same content',
            'orig_id': str(qsd.pk), 'orig_version': '',
        })
        self.assertEqual(response.status_code, 200)
        qsd.refresh_from_db()
        self.assertEqual(qsd.content, 'same content')

    def test_post_revert_forbidden_without_edit_permission(self):
        self.make_page('qsdcoveragetest/norevertperm')
        self.login_nonadmin()
        response = self.client.post('/qsdcoveragetest/norevertperm.history.html', {
            'post_revert': '1', 'version_id': '1', 'orig_id': '', 'orig_version': '',
        })
        self.assertEqual(response.status_code, 403)

    def test_history_preview_with_non_numeric_version_is_404(self):
        self.make_page('qsdcoveragetest/badpreview')
        self.login_admin()
        response = self.client.get('/qsdcoveragetest/badpreview.history.html?preview=notanumber')
        self.assertEqual(response.status_code, 404)

    def test_edit_of_existing_page_forbidden_without_edit_permission(self):
        self.make_page('qsdcoveragetest/existingnoedit')
        self.login_nonadmin()
        response = self.client.get('/qsdcoveragetest/existingnoedit.edit.html')
        self.assertEqual(response.status_code, 403)

    def test_unexpected_action_404s(self):
        self.make_page('qsdcoveragetest/unexpectedaction')
        self.login_admin()
        response = self.client.get('/qsdcoveragetest/unexpectedaction.bogus.html')
        self.assertEqual(response.status_code, 404)

    def test_ajax_qsd_requires_login(self):
        self.client.logout()
        response = self.client.post('/admin/ajax_qsd', {
            'cmd': 'update', 'url': 'qsdcoveragetest/anonupdate', 'data': 'x',
            'orig_id': '', 'orig_version': '',
        }, HTTP_REFERER='/qsdcoveragetest/somepage.html')
        self.assertEqual(response.status_code, 401)

    def test_ajax_update_forbidden_without_edit_permission(self):
        self.login_nonadmin()
        response = self.client.post('/admin/ajax_qsd', {
            'cmd': 'update', 'url': 'qsdcoveragetest/ajaxnoedit', 'data': 'x',
            'orig_id': '', 'orig_version': '',
        }, HTTP_REFERER='/qsdcoveragetest/somepage.html')
        self.assertEqual(response.status_code, 403)

    def test_ajax_update_sanitizes_class_qsd_content(self):
        self.login_admin()
        response = self.client.post('/admin/ajax_qsd', {
            'cmd': 'update', 'url': 'qsdcoveragetest/ajaxclasses',
            'data': '<script>alert(1)</script>Hello', 'orig_id': '', 'orig_version': '',
        }, HTTP_REFERER='/manage/Prog/2026/Classes/somepage.html')
        self.assertEqual(response.status_code, 200)
        saved = QuasiStaticData.objects.get(url='qsdcoveragetest/ajaxclasses')
        self.assertNotIn('<script>', saved.content)
        self.assertIn('Hello', saved.content)

    def test_ajax_update_conflict_against_deleted_row_has_no_history(self):
        """
        Exercises _qsd_conflict_payload's "no recent edits to list" branch:
        the row was deleted (not just edited), so conflict.history is empty
        and the "Recent edits:" section must be omitted from the message.
        """
        self.login_admin()
        url = 'qsdcoveragetest/ajaxdeletedconflict'
        qsd = QuasiStaticData(url=url, author=self.admin, nav_category=self.nav_category,
                               content='v1', title='t', description='', keywords='')
        qsd.save()
        orig_id, orig_version = str(qsd.pk), ''
        QuasiStaticData.objects.filter(url=url).delete()

        response = self.client.post('/admin/ajax_qsd', {
            'cmd': 'update', 'url': url, 'data': 'my-edit',
            'orig_id': orig_id, 'orig_version': orig_version,
        }, HTTP_REFERER='/qsdcoveragetest/somepage.html')

        self.assertEqual(response.status_code, 409)
        payload = json.loads(response.content.decode('utf-8'))
        self.assertNotIn('Recent edits:', payload['message'])
        self.assertEqual(payload['orig_id'], '')

    def test_ajax_history_forbidden_without_edit_permission(self):
        self.login_nonadmin()
        response = self.client.post('/admin/ajax_qsd', {
            'cmd': 'history', 'url': 'qsdcoveragetest/ajaxhistorynoedit',
        }, HTTP_REFERER='/qsdcoveragetest/somepage.html')
        self.assertEqual(response.status_code, 403)

    def test_ajax_preview_version_forbidden_without_edit_permission(self):
        self.login_nonadmin()
        response = self.client.post('/admin/ajax_qsd', {
            'cmd': 'preview_version', 'url': 'qsdcoveragetest/ajaxpreviewnoedit', 'version_id': '1',
        }, HTTP_REFERER='/qsdcoveragetest/somepage.html')
        self.assertEqual(response.status_code, 403)

    def test_ajax_qsd_unknown_command_returns_empty_result(self):
        self.login_admin()
        response = self.client.post('/admin/ajax_qsd', {
            'cmd': 'not_a_real_command', 'url': 'qsdcoveragetest/unknowncmd',
        }, HTTP_REFERER='/qsdcoveragetest/somepage.html')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode('utf-8')), {})

    def test_ajax_qsd_preview_renders_markdown(self):
        response = self.client.post('/admin/ajax_qsd_preview', {
            'data': '**bold markdown**',
        }, HTTP_REFERER='/qsdcoveragetest/somepage.html')
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode('utf-8'))
        self.assertIn('<strong>bold markdown</strong>', payload['content'])

    def test_ajax_qsd_preview_sanitizes_class_qsd_content(self):
        response = self.client.post('/admin/ajax_qsd_preview', {
            'data': '<script>alert(1)</script>Hello',
        }, HTTP_REFERER='/manage/Prog/2026/Classes/somepage.html')
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode('utf-8'))
        self.assertNotIn('<script>', payload['content'])
        self.assertIn('Hello', payload['content'])

