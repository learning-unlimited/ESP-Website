from django.db import models
from django.contrib.auth.models import User

# Create your models here.

# aseering 6/15/2006: Subclassing is broken in Django, so we aren't likely to use this code as-is.  It's kept for historical reasons, until I feel like either rewriting it or deleting it, or until it works with a newer Django version.

class WebUsers(User):
    class Admin:
        pass

class GodUsers(User):
    class Admin:
        pass



