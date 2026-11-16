import logging
import unittest

from esp.utils.try_multi import try_multi

logger = logging.getLogger("esp.utils.try_multi")


class TryMultiTestCase(unittest.TestCase):
    def test_success_on_first_try(self):
        calls = {"n": 0}

        @try_multi(3)
        def succeeds():
            calls["n"] += 1
            return "ok"

        self.assertEqual(succeeds(), "ok")
        self.assertEqual(calls["n"], 1)

    def test_success_after_retries(self):
        calls = {"n": 0}

        @try_multi(3)
        def retry_success():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("temporary error")
            return "recovered"

        with self.assertLogs(logger.name, level="WARNING") as cm:
            result = retry_success()
        self.assertEqual(result, "recovered")
        self.assertEqual(calls["n"], 3)
        self.assertEqual(len(cm.output), 2)
        self.assertIn("Attempt 1/3 for retry_success failed with ValueError", cm.output[0])
        self.assertIn("Attempt 2/3 for retry_success failed with ValueError", cm.output[1])

    def test_exhaustion_raises_and_logs_error(self):
        calls = {"n": 0}

        @try_multi(3)
        def always_fails():
            calls["n"] += 1
            raise RuntimeError(f"error on attempt {calls['n']}")

        with self.assertLogs(logger.name, level="WARNING") as cm:
            with self.assertRaises(RuntimeError) as ctx:
                always_fails()

        self.assertEqual(str(ctx.exception), "error on attempt 3")
        self.assertEqual(calls["n"], 3)
        # 2 warnings for retry attempts + 1 error for exhaustion
        self.assertEqual(len(cm.output), 3)
        self.assertIn("WARNING", cm.output[0])
        self.assertIn("WARNING", cm.output[1])
        self.assertIn("ERROR", cm.output[2])
        self.assertIn("All 3 attempts for always_fails failed with RuntimeError", cm.output[2])

    def test_unexpected_exception_raises_immediately_when_specified(self):
        calls = {"n": 0}

        @try_multi(3, exceptions=(KeyError, ValueError))
        def flaky_bug():
            calls["n"] += 1
            if calls["n"] == 1:
                raise TypeError("real bug that should not be retried")
            return "ok"

        with self.assertRaises(TypeError):
            flaky_bug()
        # Unexpected exception must NOT be retried
        self.assertEqual(calls["n"], 1)

    def test_base_exception_not_caught_by_default(self):
        calls = {"n": 0}

        @try_multi(3)
        def interrupt():
            calls["n"] += 1
            raise KeyboardInterrupt()

        with self.assertRaises(KeyboardInterrupt):
            interrupt()
        self.assertEqual(calls["n"], 1)

    def test_system_exit_not_caught(self):
        calls = {"n": 0}

        @try_multi(3)
        def exit_call():
            calls["n"] += 1
            raise SystemExit(1)

        with self.assertRaises(SystemExit):
            exit_call()
        self.assertEqual(calls["n"], 1)

    def test_reject_base_exception_in_exceptions_arg(self):
        with self.assertRaises(TypeError):
            try_multi(3, exceptions=BaseException)

        with self.assertRaises(TypeError):
            try_multi(3, exceptions=(KeyboardInterrupt, ValueError))

        with self.assertRaises(TypeError):
            try_multi(3, exceptions="not an exception")

    def test_single_exception_type(self):
        calls = {"n": 0}

        @try_multi(2, exceptions=KeyError)
        def key_err_fn():
            calls["n"] += 1
            if calls["n"] == 1:
                raise KeyError("missing")
            return "found"

        with self.assertLogs(logger.name, level="WARNING") as cm:
            result = key_err_fn()
        self.assertEqual(result, "found")
        self.assertEqual(calls["n"], 2)
        self.assertEqual(len(cm.output), 1)
        self.assertIn("Attempt 1/2 for key_err_fn failed with KeyError", cm.output[0])

    def test_preserves_function_metadata_wraps(self):
        @try_multi(3)
        def sample_func(a, b=1):
            """Sample docstring."""
            return a + b

        self.assertEqual(sample_func.__name__, "sample_func")
        self.assertEqual(sample_func.__doc__, "Sample docstring.")

    def test_invalid_n_tries(self):
        with self.assertRaises(ValueError):
            try_multi(0)
        with self.assertRaises(ValueError):
            try_multi(-1)

    def test_single_try_failure(self):
        calls = {"n": 0}

        @try_multi(1)
        def one_try():
            calls["n"] += 1
            raise ValueError("fail")

        with self.assertLogs(logger.name, level="ERROR") as cm:
            with self.assertRaises(ValueError):
                one_try()

        self.assertEqual(calls["n"], 1)
        self.assertEqual(len(cm.output), 1)
        self.assertIn("All 1 attempts for one_try failed with ValueError", cm.output[0])

    def test_bare_decorator(self):
        calls = {"n": 0}

        @try_multi
        def bare_decorated():
            calls["n"] += 1
            if calls["n"] < 2:
                raise ValueError("once")
            return "done"

        with self.assertLogs(logger.name, level="WARNING") as cm:
            result = bare_decorated()
        self.assertEqual(result, "done")
        self.assertEqual(calls["n"], 2)
        self.assertEqual(len(cm.output), 1)
        self.assertIn("Attempt 1/3 for bare_decorated failed with ValueError", cm.output[0])
