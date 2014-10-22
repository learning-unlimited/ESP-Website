# Dockerfile for ESP Website <https://github.com/learning-unlimited/ESP-Website>

FROM ubuntu:12.04

# dependencies for building this image
RUN apt-get update && apt-get install -y git sudo openssh-server

# create local user
RUN useradd -m -s /bin/bash -d /home/vagrant -u 1000 -U vagrant && echo 'vagrant:vagrant' | chpasswd && adduser vagrant sudo

# set up SSH
RUN mkdir /var/run/sshd && sed -i 's/Port 22/Port 2222/' /etc/ssh/sshd_config

# get source code
COPY . /home/vagrant/devsite

# fix perms
RUN chown -R vagrant:vagrant /home/vagrant/devsite

# install dependencies
RUN /home/vagrant/devsite/esp/update_deps.sh --virtualenv=/home/vagrant/devsite_virtualenv
RUN /home/vagrant/devsite_virtualenv/bin/pip install fabric fabtools

# fabric setup
RUN /usr/sbin/sshd && service postgresql start && service memcached start && . /home/vagrant/devsite_virtualenv/bin/activate && cd /home/vagrant/devsite/esp && fab docker_dev_setup
