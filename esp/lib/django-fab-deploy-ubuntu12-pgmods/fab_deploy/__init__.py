# coding: utf-8
from fabric.api import *

from fab_deploy.db import mysql
from fab_deploy import pip, utils, system, crontab, vcs
