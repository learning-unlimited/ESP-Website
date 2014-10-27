# Dockerfile for ESP Website <https://github.com/learning-unlimited/ESP-Website>
#
# To build the image:
# cd /path/to/local/repository
# sudo docker build -t learning_unlimited/esp-website-base .
#
# To create and run a container from the image for the first time:
# sudo docker run -d -v /path/to/local/repository:/home/vagrant/devsite --name esp-website -p 127.0.0.1:8000:8000 -p 127.0.0.1:2222:22 learning_unlimited/esp-website-base
#
# Additional setup:
# fab --set container=docker vagrant_dev_setup
#
# You should then be able to run the code with:
# fab --set container=docker run_devserver
# fab --set container=docker manage:shell_plus
#
# You can stop and start the container with:
# sudo docker stop esp-website
# sudo docker start esp-website

FROM ubuntu:12.04

# dependencies for building this image
RUN apt-get update && apt-get install -y git sudo openssh-server

# create local user
RUN useradd -m -s /bin/bash -d /home/vagrant -u 1000 -U vagrant && echo 'vagrant:vagrant' | chpasswd && adduser vagrant sudo

# get setup scripts from source code
COPY ./esp/update_deps.sh \
     ./esp/packages_base.txt \
     ./esp/packages_base_manual_install.sh \
     ./esp/make_virtualenv.sh \
     ./esp/requirements.txt \
     /home/vagrant/devsite/esp/

# install dependencies
RUN /home/vagrant/devsite/esp/update_deps.sh --virtualenv=/home/vagrant/devsite_virtualenv

# set up SSH privilege separation directory
RUN mkdir /var/run/sshd

# run services
CMD service postgresql start && service memcached start && /usr/sbin/sshd -D
