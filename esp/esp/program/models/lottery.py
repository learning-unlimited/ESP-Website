from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django_extensions.db.fields.json import JSONField

from esp.program.models import Program
from esp.users.models import ESPUser


RUN_STATUS_CHOICES = [
    ('queued', 'Queued'),
    ('running', 'Running'),
    ('done', 'Done'),
    ('interrupted', 'Interrupted'),
    ('failed', 'Failed'),
]


class LotteryInputSnapshot(models.Model):
    """Content-addressed snapshot of a program's extracted lottery input
    *data* (not algorithm/weight params) -- see
    BaseLotteryAssignmentController.snapshot_data()/input_hash(). Identical
    data across multiple runs on the same program (e.g. iterating ILP
    objective params without the underlying preferences/schedule changing)
    shares one row -- param-iterations cost no extra snapshot storage."""

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='lottery_input_snapshots')
    input_hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # xz-compressed canonical JSON -- see
    # BaseLotteryAssignmentController.encode_snapshot_blob()/decode_snapshot_blob().
    data = models.BinaryField()

    class Meta:
        app_label = 'program'

    def __str__(self):
        return 'LotteryInputSnapshot(%s, program=%s)' % (self.input_hash[:12], self.program_id)


class LotteryRun(models.Model):
    """One async ILP lottery run against the remote solver service. The
    legacy algorithm is synchronous and not recorded here."""

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='lottery_runs')
    snapshot = models.ForeignKey(
        LotteryInputSnapshot, on_delete=models.PROTECT, to_field='input_hash',
        db_column='input_hash', related_name='runs',
    )

    # Which configured settings.LOTTERY_SOLVERS[...] entry this ran on:
    solver_name = models.CharField(max_length=64)
    solver_job_id = models.CharField(max_length=64, blank=True, null=True)

    status = models.CharField(max_length=16, choices=RUN_STATUS_CHOICES, default='queued')
    # Objective/shape + solve-control params this run was submitted with:
    params = JSONField(blank=True, null=True)
    label = models.CharField(max_length=128, blank=True, null=True)

    submitted_by = models.ForeignKey(ESPUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    submitted_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    progress_series = JSONField(blank=True, null=True, default=list)
    last_polled_at = models.DateTimeField(blank=True, null=True)

    # Sparse (student_id, section_id) pairs, populated once status is
    # terminal. Left at the field class's own default=dict for an untouched
    # row. NOTE: `default=None` does NOT work here, since
    # JSONField.get_default() runs the default through to_python(), and
    # to_python(None) is hardcoded to return {}, so a None default is
    # silently coerced back to {}. Distinguish "no result yet" (this
    # default dict) from "a real result, even an empty one"
    # (parse_solution_pairs() always returns a list) by type.
    enrolled_pairs = JSONField(blank=True, null=True)
    error = models.TextField(blank=True, null=True)

    saved_at = models.DateTimeField(blank=True, null=True)
    saved_by = models.ForeignKey(ESPUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    archived = models.BooleanField(default=False)

    class Meta:
        app_label = 'program'
        ordering = ['-submitted_at']

    def __str__(self):
        return 'LotteryRun(%s, program=%s, status=%s)' % (self.id, self.program_id, self.status)
