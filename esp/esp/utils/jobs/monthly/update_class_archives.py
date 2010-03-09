from django_extensions.management.jobs import MonthlyJob
from esp.program.models import Program, ArchiveClass
from datetime import datetime, timedelta

class Job(MonthlyJob):
    help = "Create ArchiveClass instances for all old programs"

    def execute(self):
        programs_to_archive = Program.objects.all()

        # Exclude programs that don't have any associated times/schedule yet
        programs_to_archive = programs_to_archive.filter(anchor__event__isnull=False)

        # Exclude programs that ran within the past 180 days; we're only archiving old programs
        # (This because we're bad about creating events for the later classes of long-running programs,
        # and we don't really want to archive programs that aren't over yet and so might yet be changed)
        programs_to_archive = programs_to_archive.exclude(anchor__event__end__gte=datetime.now()-timedelta(180))

        # Exclude programs that don't have any classes, since the archive is fundamentally an archive of classes
        programs_to_archive = programs_to_archive.exclude(classsubject__isnull=True)

        # Exclude programs that we've already archived
        # Note that this excludes programs that have been partially archived, from getting auto-re-archived.
        # This is a safety feature, since it's indicative of something being borked...
        programs_to_archive = programs_to_archive.exclude(classsubject__id__in=ArchiveClass.objects.all().values_list('id', flat=True))

        # 'Cause with all these joins, we're going to have duplicates
        programs_to_archive = programs_to_archive.distinct()

        print "Archiving programs:\n" + "\n".join(str(x) for x in programs_to_archive)

        for p in programs_to_archive:
            p.archive()
