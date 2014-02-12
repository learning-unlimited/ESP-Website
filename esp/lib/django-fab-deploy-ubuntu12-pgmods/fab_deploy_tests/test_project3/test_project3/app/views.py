# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import TestModel

def get_all(request):
    names = TestModel.objects.order_by('created_at').values_list('name', flat=True)
    return HttpResponse('\n'.join(names))

@csrf_exempt
@require_POST
def create(request, name):
    TestModel.objects.create(name=name)
    return HttpResponse('ok')

