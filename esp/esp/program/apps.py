from esp.utils.apps import InstallConfig

class ProgramConfig(InstallConfig):
    name = 'esp.program'

    def ready(self):
        super().ready()
        try:
            from esp.program.models.printable_job import PrintableJob
            # Reset stuck jobs on server startup
            PrintableJob.objects.filter(status__in=['PENDING', 'PROCESSING']).update(
                status='FAILED',
                error_message='Server restarted while job was in progress.'
            )
        except Exception:
            # Avoid crashing startup if DB is not ready (e.g. during migrations)
            pass
