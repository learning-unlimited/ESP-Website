from django.db import models
from django.core.validators import URLValidator

class AdminToolbarLink(models.Model):
    title = models.CharField(max_length=200)
    url = models.CharField(max_length=500, validators=[URLValidator()])
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = "Admin Toolbar Link"
        verbose_name_plural = "Admin Toolbar Links"

    def __str__(self):
        return self.title