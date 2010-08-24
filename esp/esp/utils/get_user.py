#!/usr/bin/python

## Pull this function out into its own file so that it's not in any one 
## file s.t. a circular dependency is created when everyone tries to 
## import that one file and that one file tries to import someone

from esp.cache import cache_function
from esp.users.models import ESPUser
from django.contrib.auth.models import User

@cache_function
def get_user(user_id):
    global ESPUser
    if not ESPUser:
        from esp.users.models import ESPUser
    return ESPUser.objects.get(id=user_id)
get_user.depend_on_row(lambda: User, lambda user: {'user_id': user.id})
