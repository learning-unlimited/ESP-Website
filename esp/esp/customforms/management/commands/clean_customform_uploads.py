from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from esp.customforms.DynamicForm import ComboForm


class Command(BaseCommand):
    help = ("Deletes the temporary custom form uploads left behind by form "
            "wizard sessions that were never completed or restarted")

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=48,
            help='Delete temp uploads last modified more than this many hours ago (default: 48).'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Report what would be deleted without deleting anything."
        )

    def handle(self, *args, **options):
        storage = ComboForm.file_storage
        dry_run = options['dry_run']
        cutoff = timezone.now() - timedelta(hours=options['hours'])

        if not storage.exists(''):
            self.stdout.write("No temp upload directory yet; nothing to do.")
            return

        # listdir is non-recursive, which is all we need: the wizard saves
        # every temp upload as a flat name in the root of this storage.
        dirs, filenames = storage.listdir('')
        count = 0
        for filename in filenames:
            # get_modified_time() and timezone.now() agree on awareness,
            # since both follow settings.USE_TZ.
            if storage.get_modified_time(filename) >= cutoff:
                continue
            self.stdout.write(f"Deleting orphaned temp upload {filename}")
            if not dry_run:
                storage.delete(filename)
            count += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Would have deleted {count} orphaned temp upload(s)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Deleted {count} orphaned temp upload(s)."))
