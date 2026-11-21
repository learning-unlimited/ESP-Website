"""Sends queued print jobs to network printers (see
esp.program.controllers.printing). Runs until stopped; on esp-web it runs as
the esp-print-worker systemd service (deploy/config_templates/
esp-print-worker.service), and on dev VMs too (fab installs it, with
--autoreload so code changes restart it like runserver)."""
from __future__ import absolute_import

import logging
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send queued day-of print jobs to network printers, forever (or once with --once).'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Do one pass and exit.')
        parser.add_argument('--interval', type=float, default=3.0, help='Seconds between passes.')
        parser.add_argument('--autoreload', action='store_true',
                            help='Restart when the code changes, like runserver (for development).')

    def handle(self, *args, **options):
        if options['autoreload'] and not options['once']:
            from django.utils import autoreload
            autoreload.main(self.run, kwargs=options)
        else:
            self.run(**options)

    def run(self, **options):
        from esp.program.controllers import printing
        last_cleanup = 0
        while True:
            close_old_connections()
            try:
                sent = printing.run_network_jobs_once()
                if sent:
                    logger.info('Sent %d print job(s)', sent)
                if time.time() - last_cleanup > 3600:
                    printing.discard_old_uploads()
                    last_cleanup = time.time()
            except Exception:
                logger.exception('Print worker pass failed')
            if options['once']:
                return
            time.sleep(options['interval'])
