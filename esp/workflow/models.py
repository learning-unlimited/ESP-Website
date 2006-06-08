from django.db import models

# Create your models here.

class Controller(models.Model):
    temp = models.IntegerField()
    class Admin:
        pass
    
