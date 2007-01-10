from django.shortcuts import render_to_response
from esp.cal.models import Event
from esp.qsd.models import QuasiStaticData
from esp.datatree.models import GetNode, DataTree
from esp.miniblog.models import Entry
from django.http import HttpResponseRedirect, HttpResponse, Http404
from esp.users.models import ESPUser, UserBit, GetNodeOrNoBits
from esp.program.models import Class
from django import forms

from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.decorators import login_required
from esp.web.models import NavBarEntry

@login_required
def updateClass(request, id):
    """ An update-class form """
    try:
        manipulator = Class.ChangeManipulator(id)
    except Class.DoesNotExist:
        raise Http404

    curUser = ESPUser(request.user)
    if not curUser.canEdit(Class.objects.get(id=id)):
        raise Http404
	
    orig_class = manipulator.original_object

    #errors = None

    if request.POST:
        new_data = request.POST.copy()
        # We're not letting users change these.  Admins only, and only via the Admin interface.
        assert False, (new_data['anchor'], str(orig_class.anchor.id))
        
        new_data['anchor'] = str(orig_class.anchor.id)
        new_data['parent_program'] = str(orig_class.parent_program.id)


        errors = manipulator.get_validation_errors(new_data)

        if not errors:
            manipulator.do_html2python(new_data)

            manipulator.save(new_data)

            return HttpResponseRedirect(".")
    else:
        errors = {}
        new_data = orig_class.__dict__

    form = forms.FormWrapper(manipulator, new_data, errors)
    return render_to_response('program/class_form.html', {'form': form, 'class': orig_class, 'edit': True, 'orig_class': orig_class })


#def courseCatalogue(request, one, two):
#    """ aseering 9-1-2006 : This function appears to not be used by anything; esp.web.program contains its equivalent.
#        If nothing breaks by commenting this out, it should probably be deleted. """
#    treeItem = "Q/Programs/" + one + "/" + two 
#    prog = GetNode(treeItem).program_set.all()
#    if len(prog) < 1:
#        return render_to_response('users/construction', {'request': request,
#                                                         'logged_in': request.user.is_authenticated() })
#    prog = prog[0]
#    clas = list(prog.class_set.all().order_by('category'))
#    p = one + " " + two
#    return render_to_response('program/catalogue', {'request': request,
#                                                    'Program': p.replace("_", " "),
#			'courses': clas })


def programTemplateEditor(request):
    """ Generate and display a listing of all QSD pages in the Programs template
    (QSD pages that are created automatically when a new program is created) """
    qsd_pages = []

    template_node = GetNode('Q/Programs/Template')

    for qsd in template_node.quasistaticdata_set.all():
        qsd_pages.append( { 'edit_url': qsd.name + ".edit.html",
                            'view_url': qsd.name + ".html",
                            'page': qsd } )

    have_create = UserBit.UserHasPerms(request.user, template_node, GetNode('V/Administer/Edit'))

    return render_to_response('display/qsd_listing.html', { 'request': request,
                                                            'qsd_pages': qsd_pages, 'have_create': have_create })

def classTemplateEditor(request, program, session):
    """ Generate and display a listing of all QSD pages in the Class template within the specified program
    (QSD pages that are created automatically when a new class is created) """
    qsd_pages = []

    try:
        template_node = GetNodeOrNoBits('Q/Programs/' + program + '/' + session + '/Template', request.user)
    except DataTree.NoSuchNodeException:
        raise Http404

    for qsd in template_node.quasistaticdata_set.all():
        qsd_pages.append( { 'edit_url': qsd.name + ".edit.html",
                            'view_url': qsd.name + ".html",
                            'page': qsd } )

    have_create = UserBit.UserHasPerms(request.user, template_node, GetNode('V/Administer/Edit'))

    return render_to_response('display/qsd_listing.html', { 'request': request,
                                                            'qsd_pages': qsd_pages,
                                                            'have_create': have_create })


def programBattlescreen(request):
    """ Generate a display of an assortment of useful information for a specified program """
