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
    prog = GetNode(treeItem).program_set.all()
    if len(prog) < 1:
        return render_to_response('users/construction', {'logged_in': request.user.is_authenticated() })
    prog = prog[0]
    clas = list(prog.class_set.all().order_by('category'))
    p = one + " " + two
    return render_to_response('program/catalogue', {'Program': p.replace("_", " "),
			'courses': clas })
