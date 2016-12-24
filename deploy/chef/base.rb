#!/usr/bin/env chef-apply
#
# Installs base Ubuntu packages and configuration.

require_relative 'common'

# Set hostname.
file '/etc/hostname' do
  content unix_hostname + "\n"
  notifies :run, 'execute[hostname]', :immediately
end

template '/etc/hosts' do
  source "#{TEMPLATES}/hosts"
  local true
  variables({
    :fqdn => unix_fqdn,
    :hostname => unix_hostname,
  })
end

execute 'hostname' do
  # Set the temporary hostname based on the permanent configuration.
  command '/bin/hostname `cat /etc/hostname`'
  action :nothing
end

# Install packages. For now, pulls this list from packages_base.txt.
execute 'apt update' do
  command 'apt update'
end

File.readlines("#{REPO}/esp/packages_base.txt").each do |p|
  p.strip!
  package p
end

# Helpful packges
package 'htop'
package 'emacs'
