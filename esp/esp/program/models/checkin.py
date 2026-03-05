
from django.db import models
from esp.users.models import ESPUser
from esp.program.models.class_ import ClassSection

class ClassCheckIn(models.Model):
    """
    Records a student's check-in for a specific class section.
    """
    student = models.ForeignKey(ESPUser, on_delete=models.CASCADE, related_name='checkins')
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='checkins')
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=32, default='checked-in')

    class Meta:
        app_label = 'program'
        db_table = 'program_classcheckin'
        unique_together = ('student', 'class_section', 'status') # Prevent duplicates unless it's a different session instance (if they occur multiple times, maybe we should just use Date?, but for now keeping it simple or we can just rely on the view logic or add Date to unique_together)

    def __str__(self):
        return f"{self.student.username} checked into {self.class_section.emailcode()} at {self.timestamp}"

