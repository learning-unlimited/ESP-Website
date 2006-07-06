from django.shortcuts import render_to_response
from esp.calendar.models import Event
from esp.web.models import QuasiStaticData
from esp.datatree.models import GetNode
from esp.miniblog.models import Entry
from django.http import HttpResponse, Http404

from django.contrib.auth.models import User
from esp.web.models import NavBarEntry

def courseCatalogue(request, one, two):
    treeItem = "Q/Programs/" + one + "/" + two 
    prog = GetNode(treeItem)
    classes = prog.program_set.all()
    
    assert False
