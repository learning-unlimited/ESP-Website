from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

# Create your models here.

class BlogEntry(models.Model):
    author = models.ForeignKey(User)
    title = models.CharField(maxlength=128)
    text = models.TextField()
    timestamp = models.DateTimeField(default=datetime.now())
    class Admin:
        pass
