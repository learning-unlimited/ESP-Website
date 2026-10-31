"""
Tests for the dbmail_cron.py cron script (esp/dbmail_cron.py).

The script lives outside the esp package, but pytest.ini puts the outer esp/
directory on sys.path, so it is importable as ``dbmail_cron``.
"""
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

import dbmail_cron

LOCK_FILE_NAME = 'espweb.dbmailcron.lock'

# Holds an exclusive lock on argv[1] until stdin is closed.  fcntl locks are
# per-process, so a second instance has to be simulated in another process.
HOLD_LOCK_SCRIPT = (
    'import fcntl, sys\n'
    'f = open(sys.argv[1], "w")\n'
    'fcntl.lockf(f, fcntl.LOCK_EX)\n'
    'print("locked", flush=True)\n'
    'sys.stdin.read()\n'
)

# Exits 0 if it can take the lock on argv[1] without blocking, 1 otherwise.
TRY_LOCK_SCRIPT = (
    'import fcntl, sys\n'
    'f = open(sys.argv[1], "w")\n'
    'try:\n'
    '    fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\n'
    'except IOError:\n'
    '    sys.exit(1)\n'
)


class DbmailCronTest(SimpleTestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)
        self.lock_file_path = os.path.join(self.tmpdir, LOCK_FILE_NAME)

        patcher = patch('tempfile.gettempdir', return_value=self.tmpdir)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Attach both mocks to one parent so their relative call order is recorded.
        self.calls = MagicMock()
        for name in ('process_messages', 'send_email_requests'):
            patcher = patch('esp.dbmail.cronmail.%s' % name)
            self.calls.attach_mock(patcher.start(), name)
            self.addCleanup(patcher.stop)

    def lock_is_free(self):
        result = subprocess.run([sys.executable, '-c', TRY_LOCK_SCRIPT, self.lock_file_path])
        return result.returncode == 0

    def test_main_processes_then_sends_and_releases_lock(self):
        with self.assertLogs('esp.dbmail_cron', level='INFO') as logs:
            dbmail_cron.main()

        self.assertEqual(
            [c[0] for c in self.calls.mock_calls],
            ['process_messages', 'send_email_requests'],
        )
        self.assertTrue(os.path.exists(self.lock_file_path))
        self.assertTrue(self.lock_is_free())
        self.assertEqual(logs.output[0], 'INFO:esp.dbmail_cron:dbmail_cron: starting!')
        self.assertEqual(logs.output[-1], 'INFO:esp.dbmail_cron:dbmail_cron: done.')

    def test_main_unlocks_and_closes_lock_file(self):
        opened = []

        def tracking_open(*args, **kwargs):
            f = open(*args, **kwargs)
            opened.append(f)
            return f

        with patch('dbmail_cron.fcntl.lockf', wraps=dbmail_cron.fcntl.lockf) as mock_lockf, \
                patch('dbmail_cron.open', side_effect=tracking_open) as mock_open:
            dbmail_cron.main()

        mock_open.assert_called_once_with(self.lock_file_path, 'w')
        self.assertEqual(
            [c.args[1] for c in mock_lockf.call_args_list],
            [dbmail_cron.fcntl.LOCK_EX | dbmail_cron.fcntl.LOCK_NB, dbmail_cron.fcntl.LOCK_UN],
        )
        self.assertTrue(opened[0].closed)

    def test_main_exits_when_another_instance_holds_lock(self):
        holder = subprocess.Popen(
            [sys.executable, '-c', HOLD_LOCK_SCRIPT, self.lock_file_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        )
        try:
            self.assertEqual(holder.stdout.readline().strip(), 'locked')
            with self.assertLogs('esp.dbmail_cron', level='INFO') as logs:
                with self.assertRaises(SystemExit) as cm:
                    dbmail_cron.main()
        finally:
            holder.stdin.close()
            holder.wait()
            holder.stdout.close()

        self.assertEqual(cm.exception.code, 0)
        self.calls.process_messages.assert_not_called()
        self.calls.send_email_requests.assert_not_called()
        self.assertIn(
            'INFO:esp.dbmail_cron:dbmail_cron: exiting because another instance has the lock.',
            logs.output,
        )
        self.assertNotIn('INFO:esp.dbmail_cron:dbmail_cron: done.', logs.output)

    def test_main_logs_error_and_releases_lock_on_exception(self):
        error = RuntimeError('boom')
        self.calls.process_messages.side_effect = error

        with patch.object(dbmail_cron.logger, 'error') as mock_error, \
                patch.object(dbmail_cron.logger, 'exception') as mock_exception:
            dbmail_cron.main()

        self.calls.send_email_requests.assert_not_called()
        mock_error.assert_called_once_with('dbmail_cron: fatal error!')
        mock_exception.assert_called_once_with(error)
        self.assertTrue(self.lock_is_free())

    def run_setup(self, environ):
        with patch.dict(os.environ, environ), \
                patch.object(sys, 'path', list(sys.path)), \
                patch('django.setup') as mock_django_setup:
            dbmail_cron.setup()
            self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'esp.settings')
            self.assertEqual(sys.path[0], dbmail_cron.project)
            activated = os.environ.get('DBMAIL_CRON_TEST_ACTIVATED')
        mock_django_setup.assert_called_once_with()
        return activated

    def test_setup_uses_already_active_virtualenv(self):
        self.assertIsNone(self.run_setup({'VIRTUAL_ENV': self.tmpdir}))

    def test_setup_activates_bundled_virtualenv(self):
        # setup() looks for env/bin/activate_this.py next to the project dir.
        bin_dir = os.path.join(self.tmpdir, 'env', 'bin')
        os.makedirs(bin_dir)
        activate_this = os.path.join(bin_dir, 'activate_this.py')
        with open(activate_this, 'w') as f:
            f.write("import os\nos.environ['DBMAIL_CRON_TEST_ACTIVATED'] = __file__\n")

        with patch.object(dbmail_cron, 'project', os.path.join(self.tmpdir, 'esp')), \
                patch.dict(os.environ):
            os.environ.pop('VIRTUAL_ENV', None)
            self.assertEqual(self.run_setup({}), activate_this)

    def test_import_has_no_side_effects(self):
        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
        path = list(sys.path)

        with patch('django.setup') as mock_django_setup:
            importlib.reload(dbmail_cron)

        mock_django_setup.assert_not_called()
        self.assertEqual(os.environ.get('DJANGO_SETTINGS_MODULE'), settings_module)
        self.assertEqual(sys.path, path)
        self.calls.process_messages.assert_not_called()
        self.calls.send_email_requests.assert_not_called()
        self.assertFalse(os.path.exists(self.lock_file_path))
