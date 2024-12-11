# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = '2'

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  # Build off the basic Ubuntu 64-bit VM.
  config.vm.box = 'ubuntu-24.04'
  config.vm.box_url = 'https://learningu-static.s3.amazonaws.com/ubuntu-24.04.box'
  config.vm.hostname = 'ludev'
  config.ssh.forward_agent = true
  config.ssh.forward_x11 = true
  config.ssh.insert_key = false

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
    vb.customize ["modifyvm", :id, "--cpus", "2"]
  end

end
