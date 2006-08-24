from django.shortcuts import render_to_response
from esp.calendar.models import Event
from esp.qsd.models import QuasiStaticData
from esp.datatree.models import GetNode, DataTree
from esp.miniblog.models import Entry
from django.http import HttpResponse, Http404
from esp.users.models import UserBit, GetNodeOrNoBits

from django.contrib.auth.models import User, AnonymousUser
from esp.web.models import NavBarEntry

def courseCatalogue(request, one, two):
    treeItem = "Q/Programs/" + one + "/" + two 
    prog = GetNode(treeItem).program_set.all()
    if len(prog) < 1:
        return render_to_response('users/construction', {'request': request,
                                                         'logged_in': request.user.is_authenticated() })
    prog = prog[0]
    clas = list(prog.class_set.all().order_by('category'))
    p = one + " " + two
    return render_to_response('program/catalogue', {'request': request,
                                                    'Program': p.replace("_", " "),
			'courses': clas })


def programTemplateEditor(request):
    qsd_pages = []

    template_node = GetNode('Q/Programs/Template')

    for qsd in template_node.quasistaticdata_set.all():
        qsd_pages.append( { 'edit_url': qsd.name + ".edit.html",
                            'view_url': qsd.name + ".html",
                            'page': qsd } )

    have_create = UserBit.UserHasPerms(request.user, template_node, GetNode('V/Create'))

    return render_to_response('display/qsd_listing.html', { 'request': request,
                                                            'qsd_pages': qsd_pages, 'have_create': have_create })

def classTemplateEditor(request, program, session):
    qsd_pages = []

    try:
        template_node = GetNodeOrNoBits('Q/Programs/' + program + '/' + session + '/Template', request.user)
    except DataTree.NoSuchNodeException:
        raise Http404

    for qsd in template_node.quasistaticdata_set.all():
        qsd_pages.append( { 'edit_url': qsd.name + ".edit.html",
                            'view_url': qsd.name + ".html",
                            'page': qsd } )

    have_create = UserBit.UserHasPerms(request.user, template_node, GetNode('V/Create'))

    return render_to_response('display/qsd_listing.html', { 'request': request,
                                                            'qsd_pages': qsd_pages,
                                                            'have_create': have_create })
