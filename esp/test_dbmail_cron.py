from unittest import mock
import sys
import fcntl

# We must mock django and cronmail BEFORE importing dbmail_cron
# because dbmail_cron runs django.setup() at module level
sys.modules['django'] = mock.MagicMock()
sys.modules['esp.dbmail.cronmail'] = mock.MagicMock()

import dbmail_cron