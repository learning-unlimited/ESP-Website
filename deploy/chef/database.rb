#!/usr/bin/env chef-apply
#
# Install helper scripts for database access.

require_relative 'common'

file '/root/.pgpass' do
  content pgpass_contents
  owner 'root'
  group 'root'
  mode '0600'
end

file '/home/ubuntu/.pgpass' do
  content pgpass_contents
  owner 'ubuntu'
  group 'ubuntu'
  mode '0600'
end

template '/root/.bash_aliases' do
  source "#{TEMPLATES}/bash_aliases"
  local true
  variables({
    :host => dbconfig['host'],
    :port => dbconfig['port'],
    :user => dbconfig['user'],
    :database => dbconfig['database'],
  })
  owner 'root'
  group 'root'
  mode '0644'
end

template '/home/ubuntu/.bash_aliases' do
  source "#{TEMPLATES}/bash_aliases"
  local true
  variables({
    :host => dbconfig['host'],
    :port => dbconfig['port'],
    :user => dbconfig['user'],
    :database => dbconfig['database'],
  })
  owner 'ubuntu'
  group 'ubuntu'
  mode '0644'
end
