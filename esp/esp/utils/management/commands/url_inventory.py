"""
Write an inventory of every page on the site and the roles that should see it.

    ./manage.py url_inventory --out-dir /tmp/inventory
    ./manage.py url_inventory --program Splash/2026 --program Spark/2026

Writes inventory.csv (a manual testing checklist) and inventory.json (input
for deploy/release_testing/crawl.py). Only reads from the database.
See docs/dev/release_testing.rst.
"""

import csv
import json
import os
from datetime import datetime, timezone

from django.core.management.base import BaseCommand, CommandError

from esp.program.models import Program
from esp.utils.url_inventory import FIELDS, ROLES, build_inventory


class Command(BaseCommand):
    help = 'Write a URL x role inventory of the site (CSV checklist + JSON for the browser crawl)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--program', action='append', default=[], metavar='URL',
            help='Program URL to fill module URLs from, e.g. Splash/2026. '
                 'Repeatable. Defaults to the most recently created program.')
        parser.add_argument(
            '--no-qsd', action='store_true',
            help='Leave out QSD pages stored in the database.')
        parser.add_argument(
            '--out-dir', default='.',
            help='Directory to write inventory.csv and inventory.json into.')

    def handle(self, *args, **options):
        if options['program']:
            programs = []
            for url in options['program']:
                prog = Program.objects.filter(url=url).first()
                if prog is None:
                    raise CommandError(f'No program with URL {url!r}')
                programs.append(prog)
        else:
            latest = Program.objects.order_by('-id').first()
            programs = [latest] if latest else []

        rows = build_inventory(programs, include_qsd=not options['no_qsd'])

        os.makedirs(options['out_dir'], exist_ok=True)
        csv_path = os.path.join(options['out_dir'], 'inventory.csv')
        json_path = os.path.join(options['out_dir'], 'inventory.json')
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'programs': [p.url for p in programs],
                'roles': ROLES,
                'rows': rows,
            }, f, indent=1)

        crawlable = sum(1 for r in rows if r['crawlable'] == 'yes')
        self.stdout.write(
            f'{len(rows)} rows ({crawlable} crawlable) for programs '
            f'{", ".join(p.url for p in programs) or "(none)"}\n'
            f'Wrote {csv_path} and {json_path}')
