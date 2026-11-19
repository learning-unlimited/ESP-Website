"""Models for the check-scanning (treasury) program module.

A treasurer scans paper checks into a *batch* (one program, auto-numbered).
The browser encrypts the original images and MICR line to the treasurer's
OpenPGP key before uploading; the site stores that ciphertext on disk (see
``settings.TREASURY_DATA_DIR``), never under the public media root.  The
database holds the amounts, check numbers, confirmations and deposit slips.

Money is stored in integer cents.  Every row the API or URLs mention is
identified by a random, time-ordered ULID (``uid``); integer primary keys
stay internal.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import secrets
import time

from django.db import models

from esp.program.models import Program
from esp.users.models import ESPUser

__all__ = ['CheckBatch', 'ScannedCheck', 'DepositSlip', 'TreasuryAuditEntry', 'new_uid', 'UID_RE']

_B32 = '0123456789abcdefghjkmnpqrstvwxyz'  # Crockford base32, lower case
UID_RE = r'[0-9a-hjkmnp-tv-z]{26}'


def new_uid():
    """ULID: 48-bit millisecond timestamp + 80 random bits as 26 base32 characters (sorts by creation time)."""
    n = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    return ''.join(_B32[(n >> (5 * i)) & 31] for i in reversed(range(26)))


def _uid_field():
    return models.CharField(max_length=26, unique=True, default=new_uid, editable=False)


def _user_field():
    return models.ForeignKey(ESPUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')


class CheckBatch(models.Model):
    """One scanning session's worth of checks for a program.  ``number`` counts up within the program."""
    uid = _uid_field()
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='check_batches')
    number = models.PositiveIntegerField()
    note = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = _user_field()
    # Finalized batches are closed to scanning and edits; they can be reopened while they have no current slips.
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = _user_field()
    # "Deleted" batches are only archived: hidden, read-only and restorable.
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = _user_field()

    class Meta:
        app_label = 'program'
        unique_together = (('program', 'number'),)
        ordering = ['-id']

    def __str__(self):
        return '%s batch %d' % (self.program.niceName(), self.number)


class ScannedCheck(models.Model):
    """One scanned check.  Files live in ``<TREASURY_DATA_DIR>/checks/<uid>/``."""
    uid = _uid_field()
    batch = models.ForeignKey(CheckBatch, on_delete=models.CASCADE, related_name='checks')
    seq = models.PositiveIntegerField()  # 1, 2, 3... in scan order within the batch; what people see
    scanned_at = models.DateTimeField(auto_now_add=True)
    scanned_by = _user_field()
    scanner_seq = models.CharField(max_length=20, blank=True, default='')  # the scanner's own SequenceNumber
    check_number = models.CharField(max_length=20, blank=True, default='')
    micr_complete = models.BooleanField(default=False)  # the MICR line had no unreadable characters
    amount_cents = models.PositiveIntegerField(null=True, blank=True)  # None until someone enters it
    payee_ok = models.BooleanField(default=False)  # confirmed made out to MIT ESP
    signed_ok = models.BooleanField(default=False)
    endorsed_ok = models.BooleanField(default=False)
    voided = models.BooleanField(default=False)
    # Bumped on every edit; an edit must name the version it started from, or it is refused as stale.
    version = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = _user_field()

    class Meta:
        app_label = 'program'
        unique_together = (('batch', 'seq'),)
        ordering = ['batch_id', 'seq']

    def __str__(self):
        return '%s, check %d' % (self.batch, self.seq)


class DepositSlip(models.Model):
    """A deposit ticket made from a finalized batch.

    A batch's slips are created together as a *set* (same ``set_no``).  A set can be discarded
    (``superseded_at``) and prepared again, e.g. when the bank caps the checks per ticket; discarded
    slips are kept.
    """
    uid = _uid_field()
    batch = models.ForeignKey(CheckBatch, on_delete=models.CASCADE, related_name='slips')
    set_no = models.PositiveIntegerField(default=1)
    slip_no = models.PositiveIntegerField(default=1)  # 1..n within its set
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = _user_field()
    bag_number = models.CharField(max_length=40, blank=True, default='')
    cash_cents = models.PositiveIntegerField(default=0)
    coin_cents = models.PositiveIntegerField(default=0)
    program_name = models.CharField(max_length=200)  # as written on the ticket
    treasurer_name = models.CharField(max_length=200)
    checks = models.ManyToManyField(ScannedCheck, related_name='slips')  # kept for discarded slips too
    superseded_at = models.DateTimeField(null=True, blank=True)
    superseded_by = _user_field()

    class Meta:
        app_label = 'program'
        ordering = ['-batch_id', '-set_no', 'slip_no']

    def __str__(self):
        return '%s, slip %d.%d' % (self.batch, self.set_no, self.slip_no)


class TreasuryAuditEntry(models.Model):
    """Every change made through the treasury module.  ``detail`` is JSON and refers to rows by uid."""
    at = models.DateTimeField(auto_now_add=True)
    user = _user_field()
    username = models.CharField(max_length=150)  # kept in case the user row is later deleted
    action = models.CharField(max_length=60)
    detail = models.TextField(blank=True, default='')

    class Meta:
        app_label = 'program'
        ordering = ['-id']

    def __str__(self):
        return '%s %s %s' % (self.at, self.username, self.action)
