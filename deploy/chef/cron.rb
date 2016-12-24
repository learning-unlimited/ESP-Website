#!/usr/bin/env chef-apply
#
# Install cron scripts for the website.

require_relative 'common'

template '/etc/cron.d/esp-dbmail' do
  source "#{TEMPLATES}/dbmail.cron"
  local true

  variables({
    :offset => seeded_prng('cron').rand(5),
  })
end
