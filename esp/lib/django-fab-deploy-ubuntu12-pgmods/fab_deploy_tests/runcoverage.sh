#!/bin/sh
coverage run runtests.py $*
coverage report --include=`pwd`/../fab_deploy/*
coverage html --include=`pwd`/../fab_deploy/*
