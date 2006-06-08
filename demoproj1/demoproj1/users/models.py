from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class WebUsers(User):
    class Admin:
        pass

class GodUsers(User):
    class Admin:
        pass



