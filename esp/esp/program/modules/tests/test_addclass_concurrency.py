"""
Regression tests for concurrent student registration (ajax_addclass view).

Uses TransactionTestCase so each test runs with real commits and worker threads
see the same database semantics as production. TestCase wraps tests in a
transaction that is rolled back, which does not mix well with multi-threaded
access to the ORM.
"""

import json
import threading
import unittest

from django.db import close_old_connections, connection
from django.test import Client, TransactionTestCase

from esp.program.models import StudentRegistration
from esp.program.tests import ProgramFrameworkTest


class AddClassConcurrencyRegressionTest(TransactionTestCase):
    """
    Two threads try to grab the last seat in a section (capacity 1).

    Without row locks + a single atomic workflow, both can pass capacity checks
    and enroll; with select_for_update and transaction.atomic in addclass_logic,
    one thread should win and the other should see a full-class error.
    """

    def setUp(self):
        # SQLite ignores row locks; this regression targets backends used in production.
        if not getattr(connection.features, 'supports_select_for_update', False):
            raise unittest.SkipTest(
                'Database backend must support SELECT ... FOR UPDATE (not available on SQLite).'
            )
        super().setUp()

        pf = ProgramFrameworkTest()
        pf.setUp(
            num_students=2,
            num_teachers=1,
            classes_per_teacher=1,
            sections_per_class=1,
        )
        pf.add_user_profiles()
        pf.schedule_randomly()

        self.program = pf.program
        self.students = pf.students

        self.section = self.program.sections()[0]
        self.section.max_class_capacity = 1
        self.section.save()

        self.parent_class = self.section.parent_class
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.use_priority = False
        scrmi.save()

    def test_concurrent_addclass_last_seat(self):
        # Synchronize both workers so they hit the endpoint together, maximizing
        # contention on the locked ClassSection / ClassSubject rows.
        barrier = threading.Barrier(2, timeout=60)
        results = {}
        results_lock = threading.Lock()

        def register_attempt(user):
            """
            Each thread must use its own DB connection; close stale connections
            before ORM use in a new thread (Django docs / database reference).
            """
            close_old_connections()
            try:
                client = Client()
                # If the view raises an exception (e.g., ESPError bubbling out),
                # we still want to capture that as a failed request rather than
                # letting the exception escape the worker thread.
                client.raise_request_exception = False
                self.assertTrue(
                    client.login(username=user.username, password='password'),
                    "Couldn't log in as %s" % user.username,
                )
                barrier.wait()
                resp = client.post(
                    '/learn/%s/ajax_addclass' % self.program.getUrlBase(),
                    data={
                        'class_id': str(self.parent_class.id),
                        'section_id': str(self.section.id),
                        # Keep response JSON-only (skip ajax_schedule rendering).
                        'no_schedule': '1',
                    },
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                )
                payload = None
                try:
                    payload = json.loads(resp.content.decode('utf-8'))
                except Exception:
                    payload = None
                with results_lock:
                    results[user.id] = {
                        'status_code': resp.status_code,
                        'payload': payload,
                    }
            finally:
                close_old_connections()

        t1 = threading.Thread(
            target=register_attempt,
            args=(self.students[0],),
        )
        t2 = threading.Thread(
            target=register_attempt,
            args=(self.students[1],),
        )
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        successes = 0
        failures = 0
        for r in results.values():
            ok = (
                r['status_code'] == 200
                and isinstance(r['payload'], dict)
                and r['payload'].get('status') is True
            )
            if ok:
                successes += 1
            else:
                failures += 1

        self.assertEqual(
            successes,
            1,
            'Expected exactly one successful ajax_addclass response; got %s (results=%r)' % (successes, results),
        )
        self.assertEqual(
            failures,
            1,
            'Expected exactly one failed ajax_addclass response; got %s (results=%r)' % (failures, results),
        )

        enrollment_count = StudentRegistration.valid_objects().filter(
            section=self.section,
        ).count()
        self.assertEqual(
            enrollment_count,
            1,
            'Exactly one student should hold the single seat after concurrent addclass_logic calls.',
        )

