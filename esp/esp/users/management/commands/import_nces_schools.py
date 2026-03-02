"""
Management command to import K12 schools from NCES (National Center for Education Statistics) data.

Populates the K12School model from public and/or private school CSV files so that
student profiles and statistics can use server-side autocomplete instead of loading
50k+ options.

Data sources:
  - Public schools: https://nces.ed.gov/ccd/files.asp (CCD - Common Core of Data)
    e.g. Public School Name and Address files; column names vary by year (e.g. SCH_NAME, LCITY, LSTATE).
  - Private schools: https://nces.ed.gov/surveys/pss/pssdata.asp (PSS - Private School Universe Survey)
    e.g. pss1920_pu.csv; column names vary (e.g. PINST, PCITY, PSTABB, PNAME).

Usage:
  # Using default column names for NCES CCD public school CSV:
  python manage.py import_nces_schools --csv path/to/ccd_school_file.csv

  # Specify column names (if your CSV uses different headers):
  python manage.py import_nces_schools --csv path/to/file.csv \\
    --name-col SCH_NAME --city-col LCITY --state-col LSTATE --id-col NCESSCH

  # Private school CSV (often has different column names):
  python manage.py import_nces_schools --csv path/to/pss1920_pu.csv \\
    --name-col PNAME --city-col PCITY --state-col PSTABB --id-col PPIN

  # Dry run (no DB writes):
  python manage.py import_nces_schools --csv path/to/file.csv --dry-run

  # Limit how many rows to import (for testing):
  python manage.py import_nces_schools --csv path/to/file.csv --limit 1000
"""

import csv
import os

from django.core.management.base import BaseCommand

from esp.users.models import K12School


# Default column names for NCES CCD Public School Name and Address files
# (adjust per year; see https://nces.ed.gov/ccd/ccd_layout.asp or file layout docs)
DEFAULT_CCD_NAME = 'SCH_NAME'
DEFAULT_CCD_CITY = 'LCITY'
DEFAULT_CCD_STATE = 'LSTATE'
DEFAULT_CCD_ID = 'NCESSCH'

# Common PSS (Private School) column names
DEFAULT_PSS_NAME = 'PNAME'
DEFAULT_PSS_CITY = 'PCITY'
DEFAULT_PSS_STATE = 'PSTABB'
DEFAULT_PSS_ID = 'PPIN'


def safe_str(val):
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s not in ('M', 'N', '-1', '-2') else None


class Command(BaseCommand):
    help = 'Import K12 schools from NCES public/private school CSV files into K12School'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            required=True,
            help='Path to the CSV file (e.g. from NCES CCD or PSS).',
        )
        parser.add_argument(
            '--name-col',
            type=str,
            default=DEFAULT_CCD_NAME,
            help='CSV column name for school name (default: %s for CCD)' % DEFAULT_CCD_NAME,
        )
        parser.add_argument(
            '--city-col',
            type=str,
            default=DEFAULT_CCD_CITY,
            help='CSV column name for city (default: %s)' % DEFAULT_CCD_CITY,
        )
        parser.add_argument(
            '--state-col',
            type=str,
            default=DEFAULT_CCD_STATE,
            help='CSV column name for state (default: %s)' % DEFAULT_CCD_STATE,
        )
        parser.add_argument(
            '--id-col',
            type=str,
            default=DEFAULT_CCD_ID,
            help='CSV column name for unique school ID (default: %s)' % DEFAULT_CCD_ID,
        )
        parser.add_argument(
            '--type-col',
            type=str,
            default=None,
            help='Optional: column name for school type (e.g. Public, Private).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not write to the database; only report what would be done.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of rows to import (for testing).',
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8',
            help='CSV file encoding (default: utf-8). Try latin-1 if utf-8 fails.',
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        if not os.path.isfile(csv_path):
            self.stderr.write(self.style.ERROR('File not found: %s' % csv_path))
            return

        name_col = options['name_col']
        city_col = options['city_col']
        state_col = options['state_col']
        id_col = options['id_col']
        type_col = options['type_col']
        dry_run = options['dry_run']
        limit = options['limit']
        encoding = options['encoding']

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run: no changes will be saved.'))

        created = 0
        updated = 0
        skipped = 0
        errors = 0

        try:
            with open(csv_path, 'r', encoding=encoding, errors='replace') as f:
                # Try to detect dialect
                try:
                    dialect = csv.Sniffer().sniff(f.read(4096))
                    f.seek(0)
                except csv.Error:
                    dialect = 'excel'
                    f.seek(0)

                reader = csv.DictReader(f, dialect=dialect)
                if not reader.fieldnames:
                    self.stderr.write(self.style.ERROR('CSV has no header row or is empty.'))
                    return

                # Normalize column names: some NCES files have extra spaces
                fieldnames = [fn.strip() for fn in reader.fieldnames]
                reader.fieldnames = fieldnames

                for col in (name_col, city_col, state_col, id_col):
                    if col not in fieldnames:
                        self.stderr.write(
                            self.style.ERROR(
                                'Column "%s" not found. Available: %s'
                                % (col, ', '.join(fieldnames[:20]))
                                + (' ...' if len(fieldnames) > 20 else '')
                            )
                        )
                        return

                for row in reader:
                    if limit is not None and (created + updated + skipped) >= limit:
                        break

                    name = safe_str(row.get(name_col))
                    if not name:
                        skipped += 1
                        continue

                    city = safe_str(row.get(city_col))
                    state = safe_str(row.get(state_col))
                    if state and len(state) > 2:
                        state = state[:2].upper()
                    ext_id = safe_str(row.get(id_col))
                    school_type = safe_str(row.get(type_col)) if type_col else None

                    if dry_run:
                        created += 1
                        continue

                    school = None
                    if ext_id:
                        school = K12School.objects.filter(school_id=ext_id).first()
                    if not school and name and state:
                        # Re-import: match by name+state when no NCES ID
                        school = K12School.objects.filter(
                            name=name, state=state
                        ).first()

                    if school:
                        updated += 1
                        school.name = name
                        school.city = city
                        school.state = state
                        if school_type:
                            school.school_type = school_type
                        school.save()
                    else:
                        created += 1
                        try:
                            K12School.objects.create(
                                name=name,
                                city=city,
                                state=state,
                                school_id=ext_id or None,
                                school_type=school_type,
                            )
                        except Exception as e:
                            errors += 1
                            if errors <= 5:
                                self.stderr.write(
                                    self.style.ERROR('Error creating "%s": %s' % (name, e))
                                )

        except Exception as e:
            self.stderr.write(self.style.ERROR('Failed to read CSV: %s' % e))
            return

        self.stdout.write(
            self.style.SUCCESS(
                'Done. Created: %s, Updated: %s, Skipped: %s, Errors: %s'
                % (created, updated, skipped, errors)
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING('(Dry run: no changes were saved.)'))
