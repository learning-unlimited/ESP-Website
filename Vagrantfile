# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = '2'

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  # Build off the basic Ubuntu 20.04 64-bit VM.
  config.vm.box = 'ubuntu-20.04'
  config.vm.box_url = 'https://s3.amazonaws.com/learningu-static/ubuntu-20.04.box'
  config.vm.hostname = 'ludev'

  # Forward port for Django dev server
  config.vm.network :forwarded_port, guest: 8000, host: 8000

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.  (For debugging, not needed for HTTP/SSH)
  config.vm.network :private_network, ip: '192.168.33.10'

  # Share working directory with the guest VM, so you can edit
  # code files in your host environment.
  config.vm.synced_folder './', '/home/vagrant/devsite'

  # Provider-specific configuration: headless mode, memory
  config.vm.provider :virtualbox do |vb|
    # vb.gui = true
    vb.customize ['modifyvm', :id, '--memory', '2048']
  end

end
