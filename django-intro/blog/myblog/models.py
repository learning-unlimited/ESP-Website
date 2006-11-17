from django.db import models

# Create your models here.

class BlogEntry(models.Model):
    text = models.TextField()
    timestamp = models.DateTimeField()
    
