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
    prog = GetNode(treeItem).program_set.all()[0]
    clas = prog.claus_set.all().order_by('category')
    return render_to_response('program/catalogue', {'Program': one + " " + two,
			'courses': clas})
