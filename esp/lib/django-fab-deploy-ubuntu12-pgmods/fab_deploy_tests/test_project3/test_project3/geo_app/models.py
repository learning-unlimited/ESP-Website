# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.contrib.gis.db import models

class TestGeoModel(models.Model):
    location = models.PointField(geography=True)

    objects = models.GeoManager()
