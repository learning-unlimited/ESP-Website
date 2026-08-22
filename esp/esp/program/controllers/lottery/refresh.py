"""Guarded refresh: the single place that talks to the remote solver
service on behalf of a LotteryRun, shared by the status view and the
cron poller so N concurrent viewers/pollers only ever make one live request
to the service at a time.

1. Terminal run -> nothing to do, return as-is.
2. Fresh enough (polled within MIN_POLL_INTERVAL_SECONDS) -> return cached,
   no service call.
3. Otherwise, try a transaction-scoped Postgres advisory lock keyed on the
   run's id. Loser returns the cached row instantly (whoever's holding the
   lock is already doing the work). Winner does the actual service call
   *while holding the lock/transaction*, with mandatory connect+read
   timeouts on the request (both matter -- a missing read timeout
   reintroduces hangs). Network down/hang is caught, logged, and leaves the
   run's last-known status in place for the next poll to retry.
4. On a newly-terminal run, fetch /solution and store enrolled_pairs.
"""
from __future__ import absolute_import

import logging

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from .base import LotteryException
from .ilp import parse_solution_pairs
from .remote import RemoteSolverClient, RemoteSolverError

logger = logging.getLogger('esp.lottery.refresh')

TERMINAL_STATUSES = frozenset({'done', 'interrupted', 'failed'})
MIN_POLL_INTERVAL_SECONDS = 1.5


def _try_advisory_xact_lock(key):
    """Transaction-scoped advisory lock -- auto-releases on commit/rollback,
    including if the process crashes mid-transaction. Must be called inside
    an active transaction.atomic() block."""

    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", [key])
        return cursor.fetchone()[0]


def resolve_solver_client_by_name(solver_name, solvers=None):
    if solvers is None:
        solvers = getattr(settings, 'LOTTERY_SOLVERS', {})
    config = solvers.get(solver_name)
    if config is None:
        raise LotteryException("solver %r is not configured in settings.LOTTERY_SOLVERS" % solver_name)
    config = dict(config)
    if config.pop('noverify', False):
        config['verify'] = False
    return RemoteSolverClient(**config)


def resolve_solver_client(run):
    return resolve_solver_client_by_name(run.solver_name)


def refresh_run_from_service(run):
    """Bring `run` up to date with the solver service's view of its job.
    Safe to call from multiple processes/threads/requests concurrently for
    the same run -- at most one of them will actually hit the network."""

    if run.status in TERMINAL_STATUSES:
        return run

    now = timezone.now()
    if run.last_polled_at and (now - run.last_polled_at).total_seconds() < MIN_POLL_INTERVAL_SECONDS:
        return run

    with transaction.atomic():
        if not _try_advisory_xact_lock(run.id):
            # Someone else is already refreshing this run right now -- their
            # update will be visible on the next call.
            return run

        # Re-fetch under the lock: another process's refresh may have
        # already completed and committed between our freshness check above
        # and acquiring the lock.
        run.refresh_from_db()
        if run.status in TERMINAL_STATUSES:
            return run

        try:
            client = resolve_solver_client(run)
            status_body = client.status(run.solver_job_id)
        except (RemoteSolverError, LotteryException) as e:
            logger.warning("lottery run %s: solver unreachable: %s", run.id, e)
            run.error = "solver unreachable: %s" % e
            run.last_polled_at = now
            run.save(update_fields=['error', 'last_polled_at'])
            return run

        run.status = status_body['status']
        run.progress_series = status_body.get('progress', [])
        run.error = status_body.get('error')
        run.last_polled_at = now

        if run.status in TERMINAL_STATUSES:
            run.finished_at = now
            try:
                solution = client.solution(run.solver_job_id)
            except RemoteSolverError as e:
                logger.warning("lottery run %s: failed to fetch solution: %s", run.id, e)
                solution = None
            # `is not None`, not truthiness -- the solver only reports
            # nonzero-valued variables, so a real "nobody got assigned
            # anywhere" solution comes back as {} (falsy) but is still a
            # genuine result, distinct from solution() returning None
            # (job.solution was never set, e.g. no incumbent was ever found).
            if solution is not None:
                run.enrolled_pairs = parse_solution_pairs(solution)

        run.save()

    return run
