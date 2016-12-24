#!/usr/bin/env chef-apply
#
# Install the dependencies required to run the website (Python, etc.). Web
# servers and databases are managed separately.

require_relative 'common'

service 'uwsgi' do
  supports :status => true, :restart => true, :reload => true
end

package 'python'
package 'python-setuptools'
package 'python-pip'
execute 'pip install --upgrade pip'

# Python packages that have compiled binary dependencies will be installed with
# apt, not pip.
package 'python-psycopg2'
package 'python-pycurl'
package 'python-pylibmc'

execute 'pip install --upgrade --no-cache-dir -r requirements.txt' do
  cwd "#{REPO}/esp"
  # Note: this command will get run a lot, so make sure to pin the versions of
  # all dependencies.
end

package 'nodejs'
package 'node-less'

template "#{REPO}/esp/esp/local_settings.py" do
  source "#{TEMPLATES}/local_settings.py"
  local true
  variables({
    :hostname => http_hostname,
    :hostlabel => "#{DISPLAY.fetch('institution')} #{DISPLAY.fetch('group-name')} Site",
    :cache_prefix => unix_hostname,
    :email => DISPLAY.fetch('email'),
    :shortname => DISPLAY.fetch('group-name'),
    :institution => DISPLAY.fetch('institution'),
    :timezone => CONFIG.fetch('timezone'),
    :project_root => "#{REPO}/esp/",
    :secret_key => django_secret_key,
    :dbhost => dbconfig.fetch('host'),
    :dbport => dbconfig.fetch('port'),
    :dbuser => dbconfig.fetch('user'),
    :dbpass => dbconfig.fetch('password'),
    :dbname => dbconfig.fetch('database'),
    :emailhost => emailconfig.fetch('host'),
    :emailport => emailconfig.fetch('port').to_i,
    :emailuser => emailconfig.fetch('user'),
    :emailpass => emailconfig.fetch('password'),
    :local_settings_extra => local_settings_extra,
  })
  owner 'ubuntu'
  group 'ubuntu'
  mode '0644'
  notifies :reload, 'service[uwsgi]', :delayed
end
