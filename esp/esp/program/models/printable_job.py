import uuid
from django.db import models
from esp.program.models.program import Program
from esp.users.models.espuser import ESPUser

class PrintableJob(models.Model):
    """
    Tracks asynchronous generation of large Program Printables (like student schedules)
    so the browser and Varnish do not timeout waiting for 15+ minutes of LaTeX compilation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    user = models.ForeignKey(ESPUser, on_delete=models.CASCADE)
    job_type = models.CharField(max_length=64)
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='PENDING')
    
    # Store the finished PDF or document here once complete
    file = models.FileField(upload_to='printables_jobs/%Y/%m/%d/', blank=True, null=True)
    
    # Store error messages or stack traces if compilation fails
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'program'
        db_table = 'program_printablejob'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.job_type} for {self.program} by {self.user} ({self.status})"
