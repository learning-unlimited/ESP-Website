from django.contrib.auth.backends import ModelBackend

from esp.users.models import ESPUser

class ESPAuthBackend(ModelBackend):
    """ Subclass of Django's ModelBackend that returns an ESPUser
    instead of a User. Adapted from
    http://stackoverflow.com/questions/10682414/django-user-proxy-model-from-request """

    def get_user(self, user_id):
        try:
            return ESPUser.objects.get(id=user_id)
        except ESPUser.DoesNotExist:
            return None
