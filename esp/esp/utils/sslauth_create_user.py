#!/usr/bin/python

ESPUser = None
SSLAuthBackend = None

def find_ssl_user(ssl_info):
    ## Imports must be delayed, so that settings.py can import this file 
    global ESPUser
    if not ESPUser:
        from esp.users.models import ESPUser

    global SSLAuthBackend
    if not SSLAuthBackend:
        from sslauth.backends import SSLAuthBackend

    ## If a user with the e-mail address given in this cert, already exists,
    ## then associate this cert with that user's username.
    ## Otherwise, generate a new account.

    email = ssl_info.subject_email
    users = ESPUser.objects.filter(email__iexact=email)

    if len(users) == 0:
        return SSLAuthBackend().build_username(ssl_info)

    if len(users) == 1:
        return users[0].username

    ## We have multiple matches.
    ## Now, the fun begins!
    users_by_bits = [(u.is_superuser, u.isAdministrator(), u) for u in users]
    sorted_users = [x[2] for x in reversed(sorted(users_by_bits))]
    return sorted_users[0].username
    
