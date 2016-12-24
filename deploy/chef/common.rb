# This file is included in every Chef script.

require 'inifile'

if Etc.getpwuid.uid != 0
  abort 'ERROR: this script must be run as root'
end

REPO = File.expand_path('../../../', __FILE__)
TEMPLATES = File.join(REPO, 'deploy', 'config_templates')

INI = IniFile.load(File.expand_path('/lu/share/chapter.ini'))
if INI.nil?
  abort 'ERROR: /lu/share/chapter.ini not found'
end
CONFIG = INI['config']
DISPLAY = INI['display']

def seeded_prng(key)
  base = Digest::MD5.hexdigest(unix_hostname + key).to_i(base=16)
  Random.new(base)
end

def unix_hostname
  CONFIG.fetch('slug')
end

def unix_fqdn
  "#{unix_hostname}.learningu.org"
end

def http_hostname
  CONFIG['domain-override'] || "#{unix_hostname}.learningu.org"
end

def dbconfig
  ini = IniFile.load(File.expand_path('/lu/share/database.ini'))
  if ini.nil?
    abort 'ERROR: database.ini not found'
  end

  ini['global']
end

def emailconfig
  ini = IniFile.load(File.expand_path('/lu/share/email.ini'))
  if ini.nil?
    abort 'ERROR: email.ini not found'
  end

  ini['global']
end

def pgpass_contents
  g = dbconfig
  "#{g.fetch('host')}:#{g.fetch('port')}:#{g.fetch('database')}:#{g.fetch('user')}:#{g.fetch('password')}\n"
end

def django_secret_key
  File.open('/lu/share/django-secret-key', 'r') { |f| f.read }.strip
end

def local_settings_extra
  begin
    File.readlines(File.expand_path('/lu/share/local_settings_extra.py'))
  rescue Errno::ENOENT
    ''
  end
end
