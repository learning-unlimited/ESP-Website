from django.contrib.auth.backends import ModelBackend

from esp.users.models import ESPUser

class ESPAuthBackend(ModelBackend):
    """ Subclass of Django's ModelBackend that returns an ESPUser
    instead of a User. Adapted from
    https://stackoverflow.com/questions/10682414/django-user-proxy-model-from-request
    and from django/contrib/auth/backends.py as of 1.8.5 """

    def user_can_authenticate(self, user):
        """
        Allow inactive users to authenticate (e.g. deliberately deactivated
        accounts), but reject accounts that are awaiting email activation.
        The login form still provides the user-facing error message; this
        guard protects callers of authenticate() that bypass the form,
        such as the medicalsyncapi view.
        """
        if user.is_active:
            return True
        return not ESPUser.objects.filter(pk=user.pk).filter(ESPUser.awaiting_activation_Q()).exists()

    def get_user(self, user_id):
        try:
            return ESPUser.objects.get(id=user_id)
        except ESPUser.DoesNotExist:
            return None

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = ESPUser.objects.get_by_natural_key(username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except ESPUser.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            ESPUser().set_password(password)
