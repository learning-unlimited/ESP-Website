#!/usr/bin/env chef-apply
#
# Installs and configures memcached.

require_relative 'common'

package 'memcached'

service 'memcached' do
  supports :status => true, :restart => true
end

template '/etc/memcached.conf' do
  source "#{TEMPLATES}/memcached.conf"
  local true
  notifies :restart, 'service[memcached]', :immediately
end
