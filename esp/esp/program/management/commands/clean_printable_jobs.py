from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from esp.program.models import PrintableJob

class Command(BaseCommand):
    help = "Cleans up old PrintableJob files from disk and nulls the FileField"

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Delete files for jobs updated older than this many hours (default: 24).'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        cutoff = timezone.now() - timedelta(hours=hours)
        
        # Query for jobs that have a file and were updated before the cutoff
        jobs = PrintableJob.objects.filter(updated_at__lt=cutoff).exclude(file=None).exclude(file='')
        count = 0
        for job in jobs:
            if job.file:
                self.stdout.write(f"Deleting file for job {job.id} (updated at {job.updated_at})")
                # Deletes the file from storage and saves the model (nulling/clearing the FileField)
                job.file.delete(save=True)
                count += 1
                
        self.stdout.write(self.style.SUCCESS(f"Successfully cleaned up files and cleared FileField for {count} jobs."))
