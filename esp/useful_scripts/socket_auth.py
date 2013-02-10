#!/usr/bin/python

import sys
import os
import datetime
import traceback

if __name__ == '__main__':
    cur_file = os.path.abspath(__file__)
    django_dir = os.path.abspath(os.path.join(os.path.dirname(cur_file), '..'))
    sys.path.append(django_dir)
    sys.path.append(django_dir + 'esp/')

os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

import esp.manage
from esp.users.models import ESPUser

import socket

def return_(val, conn):
    """ Return the specified return value in the appropriate format """
    if val == True:
        conn.send("true")
        conn.close()
    elif val == False:
        conn.send("false")
        conn.close()
    else:
        conn.send(val)
        conn.close()

socket_path = sys.argv[1]

def server(socket_path):
    server_sock = socket.socket(socket.AF_UNIX)
    server_sock.bind(socket_path)
    server_sock.listen(2)
    while True:
        try:
            print ">>> accept()", datetime.datetime.now()
            conn, address = server_sock.accept()
            data = conn.makefile().read()
            args = data.strip().split('\n')
            func, args = args[0], args[1:]
            if func in funcs:
                funcs[func](conn, *args)
            else:
                return_('ERROR_Unknown_Action', conn=conn, )
        except Exception as inst:
            traceback.print_exc()
            print inst.__class__
            return_('ERROR_Internal', conn=conn, )
            print "Exiting to clean up..."
            sys.exit()

def user_exists(conn, username, *args):
    if len(ESPUser.objects.filter(username__iexact=username)[:1]) > 0:
        return_(True, conn=conn,)
    else:
        return_(False, conn=conn, )

def authenticate(conn, username, password, *args):
    from django.contrib.auth import authenticate
    print ">> Running (authenticate '%s' '[redacted]')" % (username, )
    user = authenticate(username=username, password=password)
    if user is None:
        print "> Result: %s" % (user, )
    else:
        print "> Result: '%s' ('%s')" % (user, user.__dict__, )

    if user:
        return_(True, conn=conn,)
    else:
        return_(False, conn=conn,)

def check_userbit(conn, username, qnode, vnode, *args):
    from esp.users.models import UserBit, GetNode
    print ">> Running (check_userbit '%s' '%s')" % (username, vnode, )
    user = ESPUser.objects.get(username=username)
    if UserBit.UserHasPerms(user, GetNode(qnode), GetNode(vnode), recursive_required=True):
        return_(True, conn=conn, )
    else:
        return_(False, conn=conn, )

def finger(conn, username):
    from esp.users.models import UserBit, GetNode
    print ">> Running (finger '%s')" % (username, )
    user = ESPUser.objects.get(username=username)
    ret = "%s\n%s\n%s" % (user.first_name, user.last_name, user.email, )
    return_(ret, conn=conn, )

funcs = {
    'USER EXISTS': user_exists,
    'AUTHENTICATE': authenticate,
    'CHECK USERBIT': check_userbit,
    'FINGER': finger,
}

if __name__ == '__main__':
    print "Initializing server."
    server(socket_path)
