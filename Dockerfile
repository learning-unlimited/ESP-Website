FROM ubuntu:14.04

RUN apt-get update \
	&& apt-get --yes --no-install-recommends install git python vim openssh-server software-properties-common curl cryptsetup dictionaries-common \
	&& apt-get clean
RUN curl https://bootstrap.pypa.io/get-pip.py | python
RUN pip install 'fabric<2' fabtools

RUN echo ludev > /etc/hostname
EXPOSE 22
EXPOSE 8000

RUN useradd --system --create-home --home-dir /home/vagrant --shell /bin/bash --gid root --groups sudo --uid 1000 vagrant
RUN echo 'root:vagrant' | chpasswd
RUN echo 'vagrant:vagrant' | chpasswd
RUN echo 'vagrant ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers
RUN mkdir /var/run/sshd
RUN sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
RUN su vagrant -c 'ssh-keygen -t dsa -f /home/vagrant/.ssh/id_dsa -N ""'
RUN cp /home/vagrant/.ssh/id_dsa.pub /home/vagrant/.ssh/authorized_keys

RUN mkdir -p /baserepo/esp
COPY esp/*.sh esp/*.txt /esp/
RUN su vagrant -c '/esp/update_deps.sh --virtualenv=/home/vagrant/venv'
RUN rm -Rf /baserepo/esp

COPY --chown=vagrant:root . /home/vagrant/devsite

CMD service ssh start \
	&& service postgresql start \
	&& service memcached start \
	&& (cryptsetup close encrypted_uSbDW8tk5kvDrSIQ || true) \
	&& truncate -s 4G encrypted_volume.img \
	&& mkdir -p /dev/mapper \
	&& ln -s /encrypted_volume.img /dev/mapper/ubuntu--12--vg-keep_1 \
	&& cd /home/vagrant/devsite \
	&& echo $(which fab) \
	&& su vagrant -c 'fab setup' \
	&& su vagrant -c 'fab loaddb' \
	&& su vagrant -c bash

