from esp.users.models import UserBit
from esp.middleware   import ESPError
from django.contrib.auth.decorators import login_required

def UserHasPerms(branch, verb, error_msg = 'You do not have permission to view this page.', log = False):
    """ This should be used as a decorator. It checks to see if a user has the verb
        on the branch and will complain according to the error_msg.                 """


    def _checkUserDecorator(func):

        @login_required
        def _checkUser(request, *args, **kwargs):

            if not UserBit.UserHasPerms(qsc = branch, verb = verb, user = request.user):
                raise ESPError(log), error_msg

            return func(request, *args, **kwargs)


        return _checkUser

    return _checkUserDecorator

