"""
Regression tests for concurrent student registration (addclass_logic).

Uses TransactionTestCase so each test runs with real commits and worker threads
see the same database semantics as production. TestCase wraps tests in a
transaction that is rolled back, which does not mix well with multi-threaded
access to the ORM.
"""

import threading
import unittest

from django.db import close_old_connections, connection
from django.test import RequestFactory, TransactionTestCase

from esp.middleware import ESPError
from esp.program.models import ClassSection, StudentRegistration
from esp.program.modules.handlers.studentclassregmodule import StudentClassRegModule
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
        factory = RequestFactory()
        # Synchronize both workers so they enter addclass_logic together, maximizing
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
                request = factory.post(
                    '/learn/%s/ajax_addclass' % self.program.url,
                    data={
                        'class_id': str(self.parent_class.id),
                        'section_id': str(self.section.id),
                    },
                )
                request.user = user
                barrier.wait()
                # Same entry point as ajax_addclass / addclass (unused args are optional).
                StudentClassRegModule.addclass_logic(
                    request,
                    None,
                    None,
                    None,
                    None,
                    None,
                    self.program,
                    webapp=False,
                )
                with results_lock:
                    results[user.id] = 'success'
            except ESPError:
                with results_lock:
                    results[user.id] = 'esp_error'
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

        self.assertEqual(set(results.values()), {'success', 'esp_error'})

        enrollment_count = StudentRegistration.valid_objects().filter(
            section=self.section,
        ).count()
        self.assertEqual(
            enrollment_count,
            1,
            'Exactly one student should hold the single seat after concurrent addclass_logic calls.',
        )

