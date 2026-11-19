"""Tests for the check-scanning module (esp.program.modules.handlers.checkscanmodule).

Ported from the standalone prototype's API tests, plus the website integration: who may use it, scoping
to the program in the URL, and CSRF.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile

from django.conf import settings
from django.test import Client, SimpleTestCase
from django.test.utils import override_settings

from esp.program.models import Program
from esp.program.models.treasury import CheckBatch, TreasuryAuditEntry
from esp.program.tests import ProgramFrameworkTest
from django.core.files.uploadedfile import SimpleUploadedFile

FAKE_PGP = b'\xc1\x0c' + os.urandom(200)  # starts like an OpenPGP PKESK packet
FAKE_JPEG = b'\xff\xd8\xff\xe0' + os.urandom(200)
PARTS = ('front.jpg.gpg', 'rear.jpg.gpg', 'micr.json.gpg')


def slips_body(*specs):
    # The client may send a program and treasurer; the server ignores both (program and user are known).
    return {'program_name': 'Typed By Mistake', 'treasurer_name': 'Typed By Mistake Too',
            'slips': [{'n_checks': n, 'bag_number': bag, 'cash': cash, 'coins': '0'} for n, bag, cash in specs]}


class CheckScanTestBase(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({'num_students': 1, 'num_teachers': 1, 'num_admins': 1})
        super(CheckScanTestBase, self).setUp(*args, **kwargs)
        self.data_dir = tempfile.mkdtemp()
        self.settings_override = override_settings(TREASURY_DATA_DIR=self.data_dir)
        self.settings_override.enable()
        self.admin = self.admins[0]
        self.admin.set_password('password')
        self.admin.save()
        self.assertTrue(self.client.login(username=self.admin.username, password='password'))
        self.base = '/onsite/%s/' % self.program.getUrlBase()

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.data_dir, ignore_errors=True)
        super(CheckScanTestBase, self).tearDown()

    # ---- request helpers
    def url(self, name, extra='', query=''):
        return '%scheckscan_api_%s%s%s' % (self.base, name, '/' + extra if extra else '', '?' + query if query else '')

    def get(self, name, extra='', query=''):
        return self.client.get(self.url(name, extra, query))

    def send(self, method, name, extra='', query='', body=None):
        return getattr(self.client, method)(self.url(name, extra, query), data=json.dumps(body or {}),
                                            content_type='application/json')

    def post(self, name, extra='', query='', body=None):
        return self.send('post', name, extra, query, body)

    def patch(self, name, extra='', body=None):
        return self.send('patch', name, extra, '', body)

    def new_batch(self, note=''):
        r = self.post('batches', body={'note': note})
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()['id']

    def upload(self, batch, checknum='1234', complete='1', front=FAKE_PGP, redacted=FAKE_JPEG):
        data = {'scanner_seq': '00001', 'check_number': checknum, 'micr_complete': complete,
                'front.jpg.gpg': SimpleUploadedFile('front.jpg.gpg', front),
                'rear.jpg.gpg': SimpleUploadedFile('rear.jpg.gpg', FAKE_PGP),
                'micr.json.gpg': SimpleUploadedFile('micr.json.gpg', FAKE_PGP),
                'front-redacted.jpg': SimpleUploadedFile('front-redacted.jpg', redacted),
                'rear.jpg': SimpleUploadedFile('rear.jpg', FAKE_JPEG)}
        return self.client.post(self.url('checks', batch), data)

    def ready_check(self, batch, amount='50', checknum='1234'):
        """Upload a check and fill it in completely; returns its id."""
        cid = self.upload(batch, checknum).json()['id']
        r = self.patch('check', cid, {'amount': amount, 'payee_ok': True, 'signed_ok': True, 'endorsed_ok': True})
        self.assertEqual(r.status_code, 200, r.content)
        return cid


class CheckScanAccessTest(CheckScanTestBase):
    PAGES = ['checkscan', 'checkscan_history', 'checkscan_batch/x', 'checkscan_finalize/x', 'checkscan_slips/x']

    def test_pages_render_for_admin(self):
        for page in self.PAGES:
            r = self.client.get(self.base + page)
            self.assertEqual(r.status_code, 200, page)
            self.assertContains(r, 'data-base="%s"' % self.base)
            self.assertContains(r, '/media/scripts/checkscan/')

    def test_listed_on_onsite_page(self):
        r = self.client.get(self.base + 'main')
        self.assertContains(r, 'href="%scheckscan"' % self.base)
        self.assertContains(r, 'Scan Checks')

    def test_warns_while_a_private_key_is_on_the_server(self):
        self.assertNotContains(self.client.get(self.base + 'checkscan'), 'Development key in use')
        open(os.path.join(self.data_dir, 'treasurer-dev-private.asc'), 'w').close()  # what the dev key script leaves
        for page in self.PAGES:
            self.assertContains(self.client.get(self.base + page), 'Development key in use', msg_prefix=page)

    def test_batch_page_carries_batch_id(self):
        self.assertContains(self.client.get(self.base + 'checkscan_batch/abc123'), 'data-batch-id="abc123"')

    def test_only_program_admins_may_use_it(self):
        views = ['checkscan_api_batches', 'checkscan_api_info', 'checkscan_api_key', 'checkscan_api_deposits'] + self.PAGES
        for who in (self.students[0], self.teachers[0], None):
            client = Client()
            if who:
                who.set_password('password')
                who.save()
                self.assertTrue(client.login(username=who.username, password='password'))
            for view in views:
                # Non-admins get the site's error page (or a login redirect), never the module's content.
                r = client.get(self.base + view)
                self.assertNotIn('application/json', r.get('Content-Type', ''), (who, view))
                self.assertNotIn(b'data-base=', r.content, (who, view))
            client.post(self.url('batches'), data='{}', content_type='application/json')
        self.assertEqual(CheckBatch.objects.count(), 0)

    def test_post_needs_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        self.assertTrue(client.login(username=self.admin.username, password='password'))
        r = client.post(self.url('batches'), data='{}', content_type='application/json')
        self.assertEqual(r.status_code, 403)
        page = client.get(self.base + 'checkscan')  # renders {% csrf_token %}, which is what the scripts read
        token = re.search(r"name=.csrfmiddlewaretoken. value=.([^'\"]+)", page.content.decode('utf-8')).group(1)
        r = client.post(self.url('batches'), data='{}', content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 201)

    def test_treasurer_key(self):
        self.assertEqual(self.get('key').status_code, 404)
        path = os.path.join(self.data_dir, 'treasurer.asc')
        with open(path, 'w') as f:
            f.write('-----BEGIN PGP PUBLIC KEY BLOCK-----\n')
        r = self.get('key')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'BEGIN PGP PUBLIC KEY BLOCK', r.content)

    def test_unknown_methods_and_bad_bodies(self):
        self.assertEqual(self.client.delete(self.url('batches')).status_code, 405)
        r = self.client.post(self.url('batches'), data='not json', content_type='application/json')
        self.assertEqual(r.status_code, 400)
        b = self.new_batch()
        self.assertEqual(self.post('batches', b, 'op=bogus').status_code, 400)

    def test_every_change_is_audited(self):
        b = self.new_batch()
        cid = self.upload(b).json()['id']
        self.patch('check', cid, {'amount': '50'})
        entries = list(TreasuryAuditEntry.objects.order_by('id'))
        self.assertEqual([e.action for e in entries], ['batch created', 'scanned', 'edited'])
        self.assertTrue(all(e.username == self.admin.username and e.user == self.admin for e in entries))
        self.assertEqual(json.loads(entries[2].detail)['amount'], [None, '50.00'])


class CheckScanBatchTest(CheckScanTestBase):
    def test_ids_are_ulids(self):
        b = self.new_batch()
        c1, c2 = (self.upload(b).json() for _ in range(2))
        for x in (b, c1['id'], c2['id']):
            self.assertTrue(re.match(r'^[0-9a-z]{26}$', x), x)
        self.assertEqual((c1['seq'], c2['seq']), (1, 2))  # people see 1, 2, ... per batch
        self.assertEqual(self.upload(self.new_batch()).json()['seq'], 1)
        # Integer ids aren't addressable.
        self.assertEqual(self.get('batches', '1').status_code, 404)
        self.assertEqual(self.get('check', '1', 'file=redacted').status_code, 404)
        r = self.get('check', c1['id'], 'file=redacted')
        self.assertEqual(r['Cache-Control'], 'private, no-cache')

    def test_batch_numbers_per_program(self):
        a, b = self.new_batch(), self.new_batch()
        get = lambda bid: self.get('batches', bid).json()
        self.assertEqual([get(a)['program_batch'], get(b)['program_batch']], [1, 2])
        self.assertEqual(get(a)['program_name'], self.program.niceName())
        # A client-supplied number is ignored.
        r = self.post('batches', body={'program_batch': 99}).json()
        self.assertEqual(r['program_batch'], 3)
        # Another program counts separately, and its batches can't be reached through this program's URLs.
        other = Program.objects.create(url='Other/1999', name='Other 1999', grade_min=7, grade_max=12)
        ob = CheckBatch.objects.create(program=other, number=1, created_by=self.admin)
        self.assertEqual(self.get('batches', ob.uid).status_code, 404)
        self.assertEqual(self.post('batches', ob.uid, 'op=archive').status_code, 404)
        self.assertEqual(self.get('checks', ob.uid).status_code, 404)
        self.assertEqual(self.get('zip', ob.uid).status_code, 404)
        self.assertEqual(self.get('deposits', '', 'batch=' + ob.uid).status_code, 404)
        self.assertEqual(len(self.get('batches').json()), 3)
        self.assertEqual(self.get('batches').json()[0]['program_batch'], 3)  # newest first

    def test_numbers_not_reused_after_archive(self):
        a = self.new_batch()
        self.post('batches', a, 'op=archive')
        self.assertEqual(self.post('batches').json()['program_batch'], 2)

    def test_batch_note_editable(self):
        b = self.new_batch()
        r = self.patch('batches', b, {'note': '  from  the lobby box '})
        self.assertEqual((r.status_code, r.json()['note']), (200, 'from the lobby box'))
        self.assertEqual(self.patch('batches', b, {}).status_code, 400)

    def test_archive_batch(self):
        b = self.new_batch()
        cid = self.upload(b).json()['id']
        self.patch('check', cid, {'amount': '50'})
        r = self.post('batches', b, 'op=archive').json()
        self.assertTrue(r['archived'])
        self.assertEqual(r['archived_by'], self.admin.username)
        # Nothing deleted, but its amounts leave the buttons and it is read-only.
        self.assertEqual(self.get('check', cid, 'file=redacted').status_code, 200)
        self.assertEqual(self.get('info').json()['amounts'], [])
        self.assertEqual(self.upload(b).status_code, 409)
        self.assertEqual(self.patch('check', cid, {'amount': '60'}).status_code, 409)
        self.assertEqual(self.patch('batches', b, {'note': 'x'}).status_code, 409)
        for op in ('finalize', 'reopen', 'discard'):
            self.assertEqual(self.post('batches', b, 'op=' + op).status_code, 409, op)
        self.assertEqual(self.post('batches', b, 'op=slips', body=slips_body((1, '', '0'))).status_code, 409)
        self.assertFalse(self.post('batches', b, 'op=restore').json()['archived'])
        self.assertEqual(self.patch('check', cid, {'amount': '60'}).status_code, 200)
        # A finalized batch must be reopened before it can be deleted.
        b2 = self.new_batch()
        self.ready_check(b2)
        self.assertEqual(self.post('batches', b2, 'op=finalize').status_code, 200)
        self.assertEqual(self.post('batches', b2, 'op=archive').status_code, 409)


class CheckScanCheckTest(CheckScanTestBase):
    def test_rejects_plaintext_uploads(self):
        b = self.new_batch()
        self.assertEqual(self.upload(b, front=b'\xff\xd8\xff' + b'x' * 200).status_code, 400)  # a JPEG, not ciphertext
        self.assertEqual(self.upload(b, redacted=FAKE_PGP).status_code, 400)  # redacted must be a JPEG
        self.assertEqual(self.get('checks', b).json(), [])
        self.assertEqual(os.listdir(os.path.join(self.data_dir, 'checks')) if os.path.isdir(os.path.join(self.data_dir, 'checks')) else [], [])
        self.assertEqual(self.upload(b).status_code, 201)

    def test_unwritable_data_dir_is_reported(self):
        blocker = os.path.join(self.data_dir, 'blocker')
        open(blocker, 'w').close()
        b = self.new_batch()
        with override_settings(TREASURY_DATA_DIR=os.path.join(blocker, 'sub')):  # a file can't have children
            r = self.upload(b)
        self.assertEqual(r.status_code, 500)
        self.assertIn('TREASURY_DATA_DIR', r.json()['error'])
        self.assertEqual(self.get('checks', b).json(), [])

    def test_upload_stores_files_privately(self):
        b = self.new_batch()
        cid = self.upload(b).json()['id']
        self.assertEqual(sorted(os.listdir(os.path.join(self.data_dir, 'checks', cid))),
                         sorted(PARTS + ('front-redacted.jpg', 'rear.jpg')))
        self.assertFalse(self.data_dir.startswith(os.path.abspath('public/media')))

    def test_amount_flow_and_buttons(self):
        b = self.new_batch()
        ids = [self.upload(b, checknum=str(100 + i)).json()['id'] for i in range(4)]
        for cid, amt in zip(ids, ['50', '50.00', '$1,250.5', '60']):
            r = self.patch('check', cid, {'amount': amt})
            self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.patch('check', ids[0], {'amount': '-3'}).status_code, 400)
        self.assertEqual(self.patch('check', ids[0], {'amount': '1.234'}).status_code, 400)
        self.assertEqual(self.patch('check', ids[0], {'amount': 'NaN'}).status_code, 400)
        self.assertEqual(self.get('info').json()['amounts'],
                         [{'amount': '50.00', 'count': 2}, {'amount': '60.00', 'count': 1}, {'amount': '1250.50', 'count': 1}])
        self.patch('check', ids[3], {'voided': True})
        self.assertNotIn('60.00', [x['amount'] for x in self.get('info').json()['amounts']])  # removed ones don't count
        s = self.get('batches', b).json()
        self.assertEqual((s['n_live'], s['n_need_amount'], s['total']), (3, 0, '1350.50'))

    def test_clear_amount(self):
        b = self.new_batch()
        cid = self.upload(b).json()['id']
        self.patch('check', cid, {'amount': '50'})
        r = self.patch('check', cid, {'amount': None})
        self.assertEqual((r.status_code, r.json()['amount']), (200, None))
        self.assertEqual(self.get('batches', b).json()['n_need_amount'], 1)

    def test_stale_edit_refused(self):
        b = self.new_batch()
        c = self.upload(b).json()
        self.assertEqual(c['version'], 0)
        r1 = self.patch('check', c['id'], {'amount': '50', 'version': 0})
        self.assertEqual((r1.status_code, r1.json()['version']), (200, 1))
        r2 = self.patch('check', c['id'], {'amount': '60', 'version': 0})  # a second tab's stale view
        self.assertEqual(r2.status_code, 409)
        body = r2.json()
        self.assertEqual(body['check']['amount'], '50.00')
        self.assertIn('%s changed this check' % self.admin.username, body['error'])
        self.assertEqual(self.patch('check', c['id'], {'amount': '60', 'version': 1}).json()['amount'], '60.00')

    def test_nothing_to_update(self):
        cid = self.upload(self.new_batch()).json()['id']
        self.assertEqual(self.patch('check', cid, {}).status_code, 400)

    def test_images_and_encrypted_zip(self):
        b = self.new_batch()
        self.assertEqual(self.get('zip', b).status_code, 404)
        cid = self.upload(b).json()['id']
        self.assertEqual(self.get('check', cid, 'file=redacted').content, FAKE_JPEG)
        self.assertEqual(self.get('check', cid, 'file=rear').content, FAKE_JPEG)
        self.assertEqual(self.get('check', cid, 'file=front.jpg.gpg').status_code, 400)  # ciphertext is only in the zip
        r = self.get('zip', b)
        self.assertEqual(r['Content-Type'], 'application/zip')
        z = zipfile.ZipFile(io.BytesIO(r.content))
        self.assertEqual(sorted(z.namelist()), sorted('001/%s' % p for p in PARTS))
        self.assertIn('downloaded encrypted', [e.action for e in TreasuryAuditEntry.objects.all()])


class CheckScanSlipsTest(CheckScanTestBase):
    def test_finalize_and_slips(self):
        b = self.new_batch()
        ids = [self.upload(b, checknum=str(500 + i)).json()['id'] for i in range(5)]
        for cid in ids[:4]:
            self.patch('check', cid, {'amount': '50'})
        fin = lambda: self.post('batches', b, 'op=finalize')
        self.patch('check', ids[4], {'voided': True})
        self.assertEqual(fin().status_code, 409)  # not confirmed payee/signed yet
        for cid in ids[:4]:
            self.patch('check', cid, {'payee_ok': True, 'endorsed_ok': True})
        self.assertEqual(self.get('batches', b).json()['n_need_confirm'], 4)  # each missing 'signed', counted once
        for cid in ids[:4]:
            self.assertTrue(self.patch('check', cid, {'signed_ok': True}).json()['signed_ok'])
        self.patch('check', ids[4], {'voided': False})
        self.assertEqual(fin().status_code, 409)  # check 5 has no amount
        self.assertEqual(self.post('batches', b, 'op=slips', body=slips_body((5, '1', '0'))).status_code, 409)  # not finalized
        self.patch('check', ids[4], {'voided': True})  # removed checks are left out
        self.assertTrue(fin().json()['finalized'])
        # Finalized: closed to edits and scanning.
        self.assertEqual(self.patch('check', ids[0], {'amount': '1'}).status_code, 409)
        self.assertEqual(self.upload(b).status_code, 409)
        # Reopening and finalizing again works while there are no slips.
        self.assertFalse(self.post('batches', b, 'op=reopen').json()['finalized'])
        fin()
        make = lambda *specs: self.post('batches', b, 'op=slips', body=slips_body(*specs))
        self.assertEqual(make((3, '1', '0')).status_code, 400)  # counts must add up to 4
        one = make((4, '7', '20')).json()['ids']
        self.assertEqual(len(one), 1)
        self.assertEqual(make((4, '7', '20')).status_code, 409)  # discard first
        self.assertEqual(self.post('batches', b, 'op=reopen').status_code, 409)  # has slips
        self.assertTrue(self.get('batches', b).json()['done'])
        # The bank caps checks per slip: redo as 3 + 1.
        self.assertEqual(self.post('batches', b, 'op=discard').json()['discarded'], 1)
        two = make((3, '8', '20'), (1, '9', '0')).json()['ids']
        deps = {d['id']: d for d in self.get('deposits', '', 'batch=' + b).json()}
        self.assertTrue(deps[one[0]]['superseded'])
        self.assertEqual(deps[one[0]]['n_checks'], 4)  # a discarded slip keeps its checks
        self.assertEqual([(deps[i]['slip_no'], deps[i]['n_in_set'], deps[i]['n_checks'], deps[i]['total']) for i in two],
                         [(1, 2, 3, '170.00'), (2, 2, 1, '50.00')])
        self.assertEqual(self.get('checks', b).json()[3]['deposit'], two[1])
        txt = self.get('deposits', two[0], 'format=txt').content.decode('utf-8')
        self.assertIn('ticket 1 of 2', txt)
        self.assertIn('Bag #:         8', txt)
        self.assertNotIn('DISCARDED', txt)
        self.assertIn('Prepared By:   MIT ESP', txt)
        lines = txt.splitlines()
        self.assertEqual([l.split()[:2] for l in lines[-3:]], [['1', '500'], ['2', '501'], ['3', '502']])  # one check per line
        self.assertTrue(any(l.startswith('Total items') and l.endswith('3') for l in lines))
        self.assertTrue(any(l.startswith('TOTAL') and l.endswith('$170.00') for l in lines))
        detail = self.get('deposits', two[1]).json()
        self.assertEqual(detail['total_items'], 1)
        self.assertEqual(detail['checks'], [{'line': 1, 'seq': 4, 'check_number': '503', 'amount': '50.00'}])
        self.assertEqual((detail['account_label'], detail['n_in_set']), ('MIT ESP 2720107', 2))
        self.assertIn('DISCARDED', self.get('deposits', one[0], 'format=txt').content.decode('utf-8'))
        # The bag number is optional.
        self.post('batches', b, 'op=discard')
        three = make((4, '', '0')).json()['ids']
        self.assertIn('Bag #:         —', self.get('deposits', three[0], 'format=txt').content.decode('utf-8'))
        self.assertIn('attachment', self.get('deposits', two[0], 'format=txt&download=1')['Content-Disposition'])
        self.assertEqual(self.get('deposits', two[0], 'format=exe').status_code, 400)
        self.assertEqual(self.get('info').json()['treasurer_name'], self.admin.nonblank_name())
        # The program on the ticket is always the program's own, whatever the client sends.
        self.assertEqual(detail['program_name'], self.program.niceName())
        self.assertNotIn('Typed By Mistake', txt)
        # The treasurer on the ticket is the user preparing it, whatever the client sends.
        self.assertEqual(detail['deposited_by'], self.admin.nonblank_name())
        self.assertNotIn('Typed By Mistake', txt)

    def test_slip_pdf(self):
        b = self.new_batch()
        for i in range(60):
            self.ready_check(b, '150', str(700 + i))
        self.post('batches', b, 'op=finalize')
        dep = self.post('batches', b, 'op=slips', body=slips_body((60, '', '0'))).json()['ids'][0]
        r = self.get('deposits', dep, 'format=pdf')
        self.assertEqual((r.status_code, r['Content-Type']), (200, 'application/pdf'))
        self.assertEqual(r.content[:5], b'%PDF-')
        self.assertIn('inline', r['Content-Disposition'])
        self.assertIn('attachment', self.get('deposits', dep, 'format=pdf&download=1')['Content-Disposition'])


class DevTreasuryKeyScriptTest(SimpleTestCase):
    """deploy/make_dev_treasury_key.sh gives a dev VM a throwaway key pair, once, and never touches a real key."""
    script = os.path.join(settings.PROJECT_ROOT, '..', 'deploy', 'make_dev_treasury_key.sh')

    def setUp(self):
        if not shutil.which('gpg'):
            self.skipTest('gpg is not installed')
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)

    def run_script(self):
        return subprocess.run(['bash', self.script, self.dir], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)

    def test_creates_a_working_pair_once(self):
        first = self.run_script()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn('WARNING', first.stderr)
        self.assertIn('NOT', first.stderr)
        pub, priv = os.path.join(self.dir, 'treasurer.asc'), os.path.join(self.dir, 'treasurer-dev-private.asc')
        with open(pub) as f:
            self.assertIn('BEGIN PGP PUBLIC KEY BLOCK', f.read())
        with open(priv) as f:
            self.assertIn('BEGIN PGP PRIVATE KEY BLOCK', f.read())
        self.assertEqual(os.stat(priv).st_mode & 0o777, 0o600)
        before = (open(pub).read(), open(priv).read())
        second = self.run_script()
        self.assertEqual((second.returncode, second.stdout, second.stderr), (0, '', ''))
        self.assertEqual((open(pub).read(), open(priv).read()), before)

    def test_never_runs_over_an_existing_public_key(self):
        pub = os.path.join(self.dir, 'treasurer.asc')
        with open(pub, 'w') as f:
            f.write('the real treasurer key')
        r = self.run_script()
        self.assertEqual((r.returncode, r.stderr), (0, ''))
        self.assertEqual(open(pub).read(), 'the real treasurer key')
        self.assertFalse(os.path.exists(os.path.join(self.dir, 'treasurer-dev-private.asc')))
