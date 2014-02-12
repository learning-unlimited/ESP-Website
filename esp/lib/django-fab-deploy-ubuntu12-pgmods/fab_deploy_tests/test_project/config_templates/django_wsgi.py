import os
import sys
import site

# prevent errors with 'print' commands
sys.stdout = sys.stderr

# adopted from http://code.google.com/p/modwsgi/wiki/VirtualEnvironments
def add_to_path(dirs):
    # Remember original sys.path.
    prev_sys_path = list(sys.path)

    # Add each new site-packages directory.
    for directory in dirs:
        site.addsitedir(directory)

    # Reorder sys.path so new directories at the front.
    new_sys_path = []
    for item in list(sys.path):
        if item not in prev_sys_path:
            new_sys_path.append(item)
            sys.path.remove(item)
    sys.path[:0] = new_sys_path

add_to_path([
     os.path.normpath('{{ ENV_DIR }}/lib/python2.5/site-packages'),
     os.path.normpath('{{ ENV_DIR }}/lib/python2.6/site-packages'),
     os.path.normpath('{{ ENV_DIR }}/lib/python2.7/site-packages'),

     os.path.normpath('{{ PROJECT_DIR }}' + '/..'), # <- remove this line if django >= 1.4
     '{{ PROJECT_DIR }}',
])

# django < 1.4 wsgi setup
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

# django >= 1.4 wsgi setup: remove "<1.4 wsgi setup" above, uncomment the
# following line and set proper your project's name:

# from my_project.wsgi import application