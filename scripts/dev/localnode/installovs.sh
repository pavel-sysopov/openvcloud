#!/bin/bash
echo 'deb http://apt.openvstorage.com fargo main' > /etc/apt/sources.list.d/ovsaptrepo.list

apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0F18F826B6183F53
apt-get update

echo 'Package: *
Pin: origin apt.openvstorage.com
Pin-Priority: 1000
' > /etc/apt/preferences

red="/etc/systemd/system/redis-server.service.d/"
mkdir -p $red
echo '[Service]' > $red/redis.override.conf
echo 'PrivateDevices=no' >> $red/redis.override.conf


apt-get install -y volumedriver-no-dedup-server
apt-get install -y openvstorage-hc
