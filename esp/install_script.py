#!/usr/bin/env python
import getpass, sys, os, commands

print "This install script should help you with the configuration for ESP.\n\n"
password = False

slash = (os.name == 'nt' or os.name == 'dos') and '\\' or '/'
esp_path  = sys.path[0]
host_name = commands.getoutput('uname -n').strip()

cmds = ['settings','db_settings','apache']

if len(sys.argv) < 2 or sys.argv[1].lower() not in cmds:
    print """Usage: %s OPTION

Where OPTION is one of:
   settings - Save a default settings file to settings.py
   db_settings - Save a default database_settings.py file
                 to database_settings.py
   apache   - Print a virtual host configuration file for ESP
"""
    sys.exit(1)

def gen_settings():

            
    dst_fname = esp_path+'%sesp%ssettings.py' % (slash, slash)
    fname = esp_path+'%ssettings_files%sdefault_%s' % (slash, slash,host_name)
    rel_fname = '../settings_files/default_%s' % (host_name)
    
    print " Saving new settings to %s" % fname
    
    f = open(fname, 'w')
    for line in open(esp_path+'%ssettings_files%sdefault_production' % \
                     (slash,slash)):
        if line[:8] == 'ESP_ROOT':
            f.write('ESP_ROOT = "%s"' % (esp_path))
        else:
            f.write(line)
    f.close()
    if os.name == 'nt' or os.name == 'dos':
        os.system('move %s %s-old' % (dst_fname, dst_fname))
        os.system('copy %s %s' % (fname, dst_fname))
    else:
        os.system('mv -f %s %s-old' % (dst_fname, dst_fname))
        os.system('ln -s %s %s' % (rel_fname, dst_fname))
    print "Done!"
    
def gen_db_settings():
    print "Before we create the database settings file, we need the db user and password from you."

    username = raw_input('Please enter a username:')
    password = False
    while 1:
        if not password:
            password = getpass.getpass()
            password2 = getpass.getpass('Password (again): ')
            if password != password2:
                sys.stderr.write("Error: Your passwords didn't match.\n")
                password = None
                continue
        if password.strip() == '':
            sys.stderr.write("Error: Blank passwords aren't allowed.\n")
            password = None
            continue
        break

    dst_fname = esp_path+'%sesp%sdatabase_settings.py' % (slash, slash)
    fname = esp_path+'%ssettings_files%sdefault_database_settings' % (slash, slash)
    print " Saving new database settings to %s" % dst_fname
    
    f = open(dst_fname, 'w')
    for line in open(fname):
        print line+'asdf'
        if line[:13] == 'DATABASE_USER':
            f.write('DATABASE_USER = "%s"' % (username))
        elif line[:17] == 'DATABASE_PASSWORD':
            f.write('DATABASE_PASSWORD = "%s"' % (password))            
        else:
            f.write(line)
    f.close()

def apache_settings():
    hostname = raw_input('Please enter a hostname (blank if default):')
    if len(hostname.strip()) == 0:
        servername = ''
    else:
        servername = 'ServerName %s' % hostname
    print \
"""<VirtualHost *:80>
  %s
  DocumentRoot %s

  <Location "/">
      SetHandler python-program
      PythonHandler django.core.handlers.modpython
      PythonPath "['%s'] + sys.path"
      SetEnv DJANGO_SETTINGS_MODULE esp.settings
      PythonDebug Off
   </Location>

  <Location "/admin/media/">
          SetHandler none
  </Location>

  <Location "/media/">
          SetHandler none
  </Location>

</VirtualHost>
""" % (servername, esp_path, esp_path+'/')
  
    
    
modules = {'settings': gen_settings,
           'db_settings': gen_db_settings,
           'apache'     : apache_settings}



modules[sys.argv[1].lower()]()
