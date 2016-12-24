#!/usr/bin/env chef-apply
#
# Installs uWSGI and configures it to serve the website.

require_relative 'common'

package 'uwsgi'
package 'uwsgi-plugin-python' do
  notifies :restart, 'service[uwsgi]', :delayed
end

service 'uwsgi' do
  supports :status => true, :restart => true, :reload => true
end

template '/etc/uwsgi/apps-available/esp.ini' do
  source "#{TEMPLATES}/uwsgi.ini"
  local true

  owner 'root'
  group 'root'
  mode '0644'
  notifies :restart, 'service[uwsgi]', :delayed
end

link '/etc/uwsgi/apps-enabled/esp.ini' do
  to '../apps-available/esp.ini'
  notifies :restart, 'service[uwsgi]', :delayed
end

file '/var/log/uwsgi/app/esp.log' do
  # By default the logfile is only readable by root. To change this, we create
  # the file now and set its group.
  group 'adm'
end

['/tmp/esp-website.log', '/tmp/esp-website.shell.log'].each do |f|
  # TODO: fix up logging so this isn't necessary
  file f do
    user 'ubuntu'
    group 'ubuntu'
  end
end
