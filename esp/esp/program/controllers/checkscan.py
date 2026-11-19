"""Business rules for the check-scanning (treasury) module.

Ported from the standalone check-scanner-web prototype.  The browser talks to the scanner directly,
encrypts the original images and MICR line to the treasurer's OpenPGP key, and uploads only ciphertext
plus a redacted front image and the (unencrypted) rear image.  This code stores those, the amount and
check number, and builds deposit slips.  It never sees an unencrypted original or MICR line.

Views live in ``esp.program.modules.handlers.checkscanmodule``; they call the functions here and turn a
``CheckScanError`` into a JSON error response.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import json
import os
import re
import shutil
import zipfile
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Case, Count, F, IntegerField, Sum, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from esp.program.models.treasury import (CheckBatch, DepositSlip, ScannedCheck, TreasuryAuditEntry, UID_RE,
                                         new_uid)

ENCRYPTED_PARTS = ('front.jpg.gpg', 'rear.jpg.gpg', 'micr.json.gpg')
REDACTED = 'front-redacted.jpg'
REAR = 'rear.jpg'                     # stored unencrypted (endorsements, bank stamps)
ACCOUNT_LABEL = 'MIT ESP 2720107'     # written on each deposit ticket so the student org office credits ESP
PREPARED_BY = 'MIT ESP'
JPEG_MAGIC = b'\xff\xd8\xff'
MAX_UPLOAD = 15 * 1024 * 1024


class CheckScanError(Exception):
    """An error the user should see; ``status`` is the HTTP status the view answers with."""

    def __init__(self, status, message, **extra):
        super(CheckScanError, self).__init__(message)
        self.status = status
        self.message = message
        self.extra = extra


# ---------------------------------------------------------------- helpers

def data_dir():
    return settings.TREASURY_DATA_DIR


def public_key_file():
    return settings.TREASURY_PUBLIC_KEY_FILE or os.path.join(data_dir(), 'treasurer.asc')


# deploy/make_dev_treasury_key.sh leaves the throwaway development key's private half here.
DEV_PRIVATE_KEY = 'treasurer-dev-private.asc'


def private_key_on_server():
    """True if a private key sits in the data directory.  That is the insecure development key a dev VM
    generates; the real treasurer's private key must never be on the server, so scans made while this is
    true aren't confidential."""
    return os.path.exists(os.path.join(data_dir(), DEV_PRIVATE_KEY))


def check_dir(uid):
    assert re.match('^%s$' % UID_RE, uid)
    return os.path.join(data_dir(), 'checks', uid)


def audit(user, action, **detail):
    TreasuryAuditEntry.objects.create(user=user, username=user.username, action=action,
                                      detail=json.dumps(detail, sort_keys=True))


def parse_cents(v, allow_zero=False):
    """Dollar string/number ('150', '150.00', '$1,250.5') -> int cents.  '' / None -> None."""
    if v is None or str(v).strip() == '':
        return None
    try:
        d = Decimal(str(v).replace('$', '').replace(',', '').strip())
    except InvalidOperation:
        raise CheckScanError(400, 'bad amount')
    if not d.is_finite() or d < 0 or (d == 0 and not allow_zero) or d >= 1000000 or d != d.quantize(Decimal('0.01')):
        raise CheckScanError(400, 'bad amount')
    return int(d * 100)


def fmt_cents(c):
    return None if c is None else '%d.%02d' % (c // 100, c % 100)


def money_txt(c):
    return '${:,}.{:02d}'.format(c // 100, c % 100)


def clean(v, n=100):
    return re.sub(r'\s+', ' ', str(v or '')).strip()[:n]


def local(dt):
    # This site runs with USE_TZ = False, so datetimes are naive local time; handle aware ones too.
    return timezone.localtime(dt) if timezone.is_aware(dt) else dt


def iso(dt):
    return local(dt).isoformat() if dt else None


def looks_like_openpgp(data):
    # An OpenPGP binary message starts with a packet tag byte with the high bit set
    # (0xC1 = new-format PKESK, 0x84/0x85 = old-format PKESK).
    return len(data) > 64 and data[0] & 0x80 and data[:3] != JPEG_MAGIC


def _name(user):
    return user.username if user else None


def get_batch(program, uid):
    try:
        return CheckBatch.objects.select_related('program').get(program=program, uid=uid)
    except (CheckBatch.DoesNotExist, ValueError):
        raise CheckScanError(404, 'no such batch')


def get_check(program, uid):
    try:
        return ScannedCheck.objects.select_related('batch').get(batch__program=program, uid=uid)
    except (ScannedCheck.DoesNotExist, ValueError):
        raise CheckScanError(404, 'no such check')


def get_slip(program, uid):
    try:
        return DepositSlip.objects.select_related('batch', 'batch__program').get(batch__program=program, uid=uid)
    except (DepositSlip.DoesNotExist, ValueError):
        raise CheckScanError(404, 'no such deposit slip')


def require_not_deleted(batch):
    if batch.archived_at:
        raise CheckScanError(409, 'this batch was deleted; restore it (History page) to make changes')


def require_open(batch):
    require_not_deleted(batch)
    if batch.finalized_at:
        raise CheckScanError(409, 'this batch has been finalized; reopen it to make changes')


def _current_slips(batch):
    return batch.slips.filter(superseded_at__isnull=True)


# ---------------------------------------------------------------- batches

def _count_if(**cond):
    return Coalesce(Sum(Case(When(then=1, **cond), default=0, output_field=IntegerField())), 0)


def _summaries(program, **filters):
    """Batches with the counts the pages need, in one query (slip counts in a second)."""
    live = {'checks__voided': False}
    rows = (CheckBatch.objects.filter(program=program, **filters).select_related('program')
            .annotate(n_checks=Count('checks'),
                      n_live=_count_if(**live),
                      n_need_amount=_count_if(checks__amount_cents__isnull=True, **live),
                      n_need_checknum=_count_if(checks__check_number='', **live),
                      n_need_confirm=Coalesce(Sum(Case(
                          When(checks__voided=False, checks__payee_ok=False, then=1),
                          When(checks__voided=False, checks__signed_ok=False, then=1),
                          When(checks__voided=False, checks__endorsed_ok=False, then=1),
                          default=0, output_field=IntegerField())), 0),
                      total_cents=Sum(Case(When(checks__voided=False, then=F('checks__amount_cents')),
                                           output_field=IntegerField()))))
    return list(rows)


def _slip_counts(batches):
    counts = dict(DepositSlip.objects.filter(batch__in=batches, superseded_at__isnull=True)
                  .values_list('batch').annotate(n=Count('id')))
    return counts


def batch_json(b, n_slips):
    n_need_confirm = b.n_need_confirm  # a CASE counts each check once, however many confirmations it lacks
    return {'id': b.uid, 'program_name': b.program.niceName(), 'program_batch': b.number,
            'created_at': iso(b.created_at), 'created_by': _name(b.created_by), 'note': b.note,
            'n_checks': b.n_checks, 'n_live': b.n_live, 'n_need_amount': b.n_need_amount,
            'n_need_checknum': b.n_need_checknum, 'n_need_confirm': n_need_confirm,
            'total': fmt_cents(b.total_cents),
            # ready: every check has an amount and number and was confirmed payable to MIT ESP, signed and endorsed
            'ready': b.n_live > 0 and b.n_need_amount == 0 and b.n_need_checknum == 0 and n_need_confirm == 0,
            # finalized: closed to scanning and edits; deposit slips can be prepared (and redone)
            'finalized': b.finalized_at is not None, 'finalized_at': iso(b.finalized_at),
            'finalized_by': _name(b.finalized_by),
            'n_slips': n_slips, 'done': n_slips > 0,
            'archived': b.archived_at is not None, 'archived_at': iso(b.archived_at),
            'archived_by': _name(b.archived_by)}


def batch_detail(program, uid):
    b = get_batch(program, uid)
    row = _summaries(program, pk=b.pk)[0]
    return batch_json(row, _slip_counts([b]).get(b.pk, 0))


def list_batches(program):
    rows = sorted(_summaries(program), key=lambda r: -r.pk)[:1000]
    counts = _slip_counts(rows)
    return [batch_json(r, counts.get(r.pk, 0)) for r in rows]


def create_batch(user, program, note=''):
    """New batch; its number is one more than the program's highest so far (archived batches count)."""
    for _ in range(5):  # unique_together guards against two people creating one at the same moment
        top = CheckBatch.objects.filter(program=program).order_by('-number').values_list('number', flat=True).first()
        number = (top or 0) + 1
        try:
            with transaction.atomic():
                b = CheckBatch.objects.create(program=program, number=number, note=clean(note, 200), created_by=user)
            break
        except IntegrityError:
            continue
    else:
        raise CheckScanError(409, 'could not assign a batch number, try again')
    audit(user, 'batch created', batch=b.uid, program=program.niceName(), number=number)
    return b


def update_note(user, program, uid, note):
    b = get_batch(program, uid)
    require_not_deleted(b)
    new = clean(note, 200)
    old, b.note = b.note, new
    b.save(update_fields=['note'])
    audit(user, 'batch edited', batch=uid, note=[old, new])
    return b


def archive_batch(user, program, uid):
    """"Delete" a batch.  Nothing is removed: it is hidden and read-only until restored."""
    b = get_batch(program, uid)
    if b.finalized_at:
        raise CheckScanError(409, 'reopen the batch (step 3) before deleting it')
    b.archived_at, b.archived_by = timezone.now(), user
    b.save(update_fields=['archived_at', 'archived_by'])
    audit(user, 'batch archived', batch=uid, number=b.number)
    return b


def restore_batch(user, program, uid):
    b = get_batch(program, uid)
    b.archived_at = b.archived_by = None
    b.save(update_fields=['archived_at', 'archived_by'])
    audit(user, 'batch restored', batch=uid)
    return b


def finalize_batch(user, program, uid):
    b = get_batch(program, uid)
    require_open(b)
    s = batch_detail(program, uid)
    if not s['ready']:
        raise CheckScanError(409, 'every check needs an amount, a check number, and all three confirmations '
                                  '(made out to MIT ESP, signed, endorsed) first')
    b.finalized_at, b.finalized_by = timezone.now(), user
    b.save(update_fields=['finalized_at', 'finalized_by'])
    audit(user, 'batch finalized', batch=uid, checks=s['n_live'], total=s['total'])
    return b


def reopen_batch(user, program, uid):
    b = get_batch(program, uid)
    require_not_deleted(b)
    if _current_slips(b).exists():
        raise CheckScanError(409, 'this batch has deposit slips; discard them before reopening')
    b.finalized_at = b.finalized_by = None
    b.save(update_fields=['finalized_at', 'finalized_by'])
    audit(user, 'batch reopened', batch=uid)
    return b


def amount_buttons(program):
    """Amounts used so far on this program's live checks: the quick-entry buttons."""
    rows = (ScannedCheck.objects.filter(batch__program=program, batch__archived_at__isnull=True, voided=False,
                                        amount_cents__isnull=False)
            .values('amount_cents').annotate(n=Count('id')).order_by('amount_cents'))
    return [{'amount': fmt_cents(r['amount_cents']), 'count': r['n']} for r in rows]


def treasurer_name(user):
    """The name written as "Deposited By" on a ticket: whoever prepares the slips."""
    return clean(user.nonblank_name(), 200)


# ---------------------------------------------------------------- checks

def check_json(c, slip_uid=None):
    return {'id': c.uid, 'seq': c.seq, 'scanned_at': iso(c.scanned_at), 'scanned_by': _name(c.scanned_by),
            'check_number': c.check_number, 'micr_complete': c.micr_complete,
            'amount': fmt_cents(c.amount_cents), 'payee_ok': c.payee_ok, 'signed_ok': c.signed_ok,
            'endorsed_ok': c.endorsed_ok, 'voided': c.voided, 'deposit': slip_uid,
            'version': c.version, 'updated_at': iso(c.updated_at), 'updated_by': _name(c.updated_by)}


def _current_slip_uids(checks):
    return dict(DepositSlip.objects.filter(checks__in=checks, superseded_at__isnull=True)
                .values_list('checks', 'uid'))


def one_check(c):
    c = ScannedCheck.objects.select_related('scanned_by', 'updated_by').get(pk=c.pk)
    return check_json(c, _current_slip_uids([c]).get(c.pk))


def list_checks(program, batch_uid):
    b = get_batch(program, batch_uid)
    checks = list(b.checks.select_related('scanned_by', 'updated_by').order_by('seq'))
    slips = _current_slip_uids(checks)
    return [check_json(c, slips.get(c.pk)) for c in checks]


def _read(upload):
    return upload.read() if upload else b''


def upload_check(user, program, batch_uid, form, files):
    """Store one scanned check.  Originals and MICR must arrive as OpenPGP ciphertext."""
    b = get_batch(program, batch_uid)
    require_open(b)
    parts = {}
    for name in ENCRYPTED_PARTS:
        data = _read(files.get(name))
        if not looks_like_openpgp(data):
            raise CheckScanError(400, '%s is missing or not OpenPGP ciphertext' % name)
        parts[name] = data
    red = _read(files.get(REDACTED))
    if red[:3] != JPEG_MAGIC:
        raise CheckScanError(400, 'redacted front image missing or not a JPEG')
    rear = _read(files.get(REAR))
    if rear[:3] != JPEG_MAGIC:
        raise CheckScanError(400, 'rear image missing or not a JPEG')
    check_number = re.sub(r'[^0-9A-Za-z-]', '', form.get('check_number', ''))[:20]

    uid = new_uid()
    d = check_dir(uid)
    try:
        os.makedirs(d)
    except OSError:
        raise CheckScanError(500, "the server can't write to its check-scan data directory (TREASURY_DATA_DIR)")
    try:
        for name, data in list(parts.items()) + [(REDACTED, red), (REAR, rear)]:
            with open(os.path.join(d, name), 'wb') as out:
                out.write(data)
        for _ in range(5):  # (batch, seq) is unique; retry if two uploads to one batch race
            top = b.checks.order_by('-seq').values_list('seq', flat=True).first()
            try:
                with transaction.atomic():
                    c = ScannedCheck.objects.create(
                        uid=uid, batch=b, seq=(top or 0) + 1, scanned_by=user,
                        scanner_seq=form.get('scanner_seq', '')[:20], check_number=check_number,
                        micr_complete=form.get('micr_complete') == '1')
                break
            except IntegrityError:
                continue
        else:
            raise CheckScanError(409, 'could not number the check, try again')
    except Exception:
        shutil.rmtree(d, ignore_errors=True)
        raise
    audit(user, 'scanned', check=uid, batch=batch_uid, seq=c.seq, check_number=check_number)
    return c


def update_check(user, program, uid, body):
    c = get_check(program, uid)
    require_open(c.batch)
    if 'version' in body and str(body['version']) != str(c.version):
        # Someone else saved this check since the editor loaded it: refuse and hand back the current state.
        who = _name(c.updated_by) or 'someone'
        raise CheckScanError(409, '%s changed this check in the meantime — it has been reloaded; '
                                  'check it and try again' % who, check=one_check(c))
    changes, new = {}, {}
    if 'amount' in body:
        cents = parse_cents(body['amount'])
        new['amount_cents'] = cents
        changes['amount'] = [fmt_cents(c.amount_cents), fmt_cents(cents)]
    if 'check_number' in body:
        n = re.sub(r'[^0-9A-Za-z-]', '', str(body['check_number']))[:20]
        new['check_number'] = n
        changes['check_number'] = [c.check_number, n]
    for flag in ('payee_ok', 'signed_ok', 'endorsed_ok', 'voided'):
        if flag in body:
            new[flag] = bool(body[flag])
            changes[flag] = [getattr(c, flag), new[flag]]
    if not new:
        raise CheckScanError(400, 'nothing to update')
    # Compare-and-set on version, so two simultaneous saves can't both win.
    n = ScannedCheck.objects.filter(pk=c.pk, version=c.version).update(
        updated_at=timezone.now(), updated_by=user, version=F('version') + 1, **new)
    if not n:
        raise CheckScanError(409, 'someone changed this check in the meantime — it has been reloaded; '
                                  'check it and try again', check=one_check(c))
    audit(user, 'edited', check=uid, **changes)
    return one_check(c)


def check_file(program, uid, name):
    """Path of one of a check's unencrypted images (REDACTED or REAR)."""
    assert name in (REDACTED, REAR)
    c = get_check(program, uid)
    p = os.path.join(check_dir(c.uid), name)
    if not os.path.exists(p):
        raise CheckScanError(404, 'no such image')
    return p


def encrypted_zip(user, program, batch_uid):
    """The batch's encrypted parts as a zip (for the treasurer to decrypt), plus a download file name."""
    b = get_batch(program, batch_uid)
    checks = list(b.checks.order_by('seq'))
    if not checks:
        raise CheckScanError(404, 'no scans in this batch')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as z:  # ciphertext doesn't compress
        for c in checks:
            for part in ENCRYPTED_PARTS:
                p = os.path.join(check_dir(c.uid), part)
                if os.path.exists(p):
                    z.write(p, '%03d/%s' % (c.seq, part))
    audit(user, 'downloaded encrypted', batch=batch_uid, checks=[c.uid for c in checks])
    name = re.sub(r'[^A-Za-z0-9.-]+', '-', '%s-batch-%d-encrypted.zip' % (program.niceName(), b.number))
    return buf.getvalue(), name


# ---------------------------------------------------------------- deposit slips
# A finalized batch is split into one or more slips (the bank caps checks per ticket).  A set of slips can
# be discarded and prepared again; discarded slips are kept, marked superseded.

def create_slips(user, program, batch_uid, body):
    """body: {slips: [{n_checks, bag_number, cash, coins}, ...]}.  The program name on the ticket is always
    the program's own and the treasurer is always the user preparing it.
    Checks go on slips in scan order; the counts must add up to the batch's non-voided checks."""
    b = get_batch(program, batch_uid)
    require_not_deleted(b)
    if not b.finalized_at:
        raise CheckScanError(409, 'finalize the batch first')
    if _current_slips(b).exists():
        raise CheckScanError(409, 'this batch already has deposit slips; discard them to prepare new ones')
    name, treasurer = program.niceName()[:200], treasurer_name(user)
    slips = body.get('slips') or []
    checks = list(b.checks.filter(voided=False).order_by('seq'))
    try:
        counts = [int(x.get('n_checks')) for x in slips]
    except (TypeError, ValueError, AttributeError):
        raise CheckScanError(400, 'each slip needs a number of checks')
    if not slips or any(n < 0 for n in counts) or sum(counts) != len(checks):
        raise CheckScanError(400, 'slip check counts must add up to %d' % len(checks))
    top = b.slips.order_by('-set_no').values_list('set_no', flat=True).first()
    made, i = [], 0
    with transaction.atomic():
        for k, (x, n) in enumerate(zip(slips, counts), 1):
            s = DepositSlip.objects.create(
                batch=b, set_no=(top or 0) + 1, slip_no=k, created_by=user, bag_number=clean(x.get('bag_number'), 40),
                cash_cents=parse_cents(x.get('cash'), allow_zero=True) or 0,
                coin_cents=parse_cents(x.get('coins'), allow_zero=True) or 0,
                program_name=name, treasurer_name=treasurer)
            s.checks.set(checks[i:i + n])
            made.append({'slip': s.uid, 'checks': [c.uid for c in checks[i:i + n]]})
            i += n
    audit(user, 'deposit slips created', batch=batch_uid, slips=made)
    return [m['slip'] for m in made]


def discard_slips(user, program, batch_uid):
    b = get_batch(program, batch_uid)
    require_not_deleted(b)
    n = _current_slips(b).update(superseded_at=timezone.now(), superseded_by=user)
    audit(user, 'deposit slips discarded', batch=batch_uid, count=n)
    return n


def _slip_totals(slip):
    agg = slip.checks.aggregate(n=Count('id'), cents=Coalesce(Sum('amount_cents'), 0))
    return agg['n'], agg['cents']


def slip_json(s):
    n_checks, checks_cents = _slip_totals(s)
    return {'id': s.uid, 'batch': {'id': s.batch.uid, 'program_name': s.batch.program.niceName(),
                                   'program_batch': s.batch.number},
            'set_no': s.set_no, 'slip_no': s.slip_no,
            'n_in_set': s.batch.slips.filter(set_no=s.set_no).count(),
            'superseded': s.superseded_at is not None, 'superseded_at': iso(s.superseded_at),
            'created_at': iso(s.created_at), 'created_by': _name(s.created_by),
            'bag_number': s.bag_number, 'program_name': s.program_name, 'treasurer_name': s.treasurer_name,
            'n_checks': n_checks, 'checks_total': fmt_cents(checks_cents), 'cash': fmt_cents(s.cash_cents),
            'coins': fmt_cents(s.coin_cents), 'total': fmt_cents(checks_cents + s.cash_cents + s.coin_cents)}


def list_slips(program, batch_uid=None):
    qs = DepositSlip.objects.filter(batch__program=program).select_related('batch', 'batch__program')
    if batch_uid:
        qs = qs.filter(batch=get_batch(program, batch_uid))
    return [slip_json(s) for s in qs]


def slip_detail(s):
    """Everything on one slip, named like the boxes on the Bank of America deposit ticket."""
    checks = list(s.checks.order_by('seq'))
    checks_cents = sum(c.amount_cents for c in checks)
    base = slip_json(s)
    return {'id': s.uid, 'batch': base['batch'], 'slip_no': s.slip_no, 'n_in_set': base['n_in_set'],
            'superseded': base['superseded'], 'program_name': s.program_name, 'account_label': ACCOUNT_LABEL,
            'prepared_by': PREPARED_BY, 'deposited_by': s.treasurer_name, 'bag_number': s.bag_number,
            'date': local(s.created_at).strftime('%m/%d/%Y'),
            'currency': fmt_cents(s.cash_cents), 'coins': fmt_cents(s.coin_cents),
            'checks_total': fmt_cents(checks_cents),
            'total': fmt_cents(s.cash_cents + s.coin_cents + checks_cents), 'total_items': len(checks),
            'checks': [{'line': i, 'seq': c.seq, 'check_number': c.check_number, 'amount': fmt_cents(c.amount_cents)}
                       for i, c in enumerate(checks, 1)]}


def _cents(a):
    return int(Decimal(a) * 100)


def slip_text(s):
    """Plain-text deposit slip, one check per line; fields named like the deposit ticket's boxes."""
    d = slip_detail(s)
    w = 15
    lines = ['%s — deposit ticket %d of %d' % (ACCOUNT_LABEL, d['slip_no'], d['n_in_set'])]
    if d['superseded']:
        lines.append('*** DISCARDED — replaced by a later set of slips; void the paper ticket ***')
    amt = lambda label, a: '%-20s%14s' % (label, money_txt(_cents(a)))
    lines += ['',
              '%-*s%s · batch %s' % (w, 'Batch:', d['batch']['program_name'], d['batch']['program_batch']),
              '%-*s%s' % (w, 'Program:', d['program_name']),
              '%-*s%s' % (w, 'Prepared By:', d['prepared_by']),
              '%-*s%s' % (w, 'Deposited By:', d['deposited_by']),
              '%-*s%s' % (w, 'Bag #:', d['bag_number'] or '—'),
              '%-*s%s' % (w, 'Date:', d['date']),
              '',
              amt('Currency', d['currency']), amt('Coins', d['coins']), amt('Checks', d['checks_total']),
              '-' * 34, amt('TOTAL', d['total']), '%-20s%14d' % ('Total items', d['total_items']), '',
              '%4s  %-14s%14s   Scan #' % ('Line', 'Check number', 'Amount')]
    lines += ['%4d  %-14s%14s   %d' % (c['line'], c['check_number'], money_txt(_cents(c['amount'])), c['seq'])
              for c in d['checks']]
    return '\n'.join(lines) + '\n'


def slip_file_name(s, kind):
    return re.sub(r'[^A-Za-z0-9.-]+', '-', 'deposit-%s-batch-%d-%s-%d' % (
        s.program_name, s.batch.number, 'ticket' if kind == 'pdf' else 'slip', s.slip_no)) + '.' + kind
