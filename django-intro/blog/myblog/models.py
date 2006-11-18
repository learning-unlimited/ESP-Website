from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class BlogEntry(models.Model):
    author = models.ForeignKey(User)
    title = models.TextField()
    text = models.TextField()
    timestamp = models.DateTimeField(default=datetime.now())
    class Admin:
        pass
