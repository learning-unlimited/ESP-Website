# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.db import models

class TestModel(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)