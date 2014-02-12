# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.http import HttpResponse
from django.contrib.gis.geos.point import Point
from .models import TestGeoModel

def distance(request):
    pnt = Point(50, 60)
    TestGeoModel.objects.get_or_create(pk=1, defaults = {'location':Point(40,30)})
    distances = TestGeoModel.objects.distance(pnt).values_list('distance', flat=True)
    return HttpResponse('\n'.join(str(int(d.km)) for d in distances))

