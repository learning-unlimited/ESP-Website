
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from esp.web.util import render_to_response
from esp.qsd.models import QuasiStaticData
from esp.qsd.forms import QSDMoveForm, QSDBulkMoveForm
from esp.datatree.models import *
from django.http import HttpResponseRedirect, Http404
from django.core.mail import send_mail
from esp.users.models import ESPUser, UserBit, GetNodeOrNoBits

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from esp.program.models import Program
from esp.program.forms import ProgramCreationForm
from esp.program.setup import prepare_program, commit_program
from esp.accounting_docs.models import Document
from esp.middleware import ESPError
from esp.accounting_core.models import LineItemType, CompletedTransactionException

import pickle

#def courseCatalogue(request, one, two):
#    """ aseering 9-1-2006 : This function appears to not be used by anything; esp.web.program contains its equivalent.
#        If nothing breaks by commenting this out, it should probably be deleted. """
#    treeItem = "Q/Programs/" + one + "/" + two 
#    prog = GetNode(treeItem).program_set.all()
#    if len(prog) < 1:
#        return render_to_response('users/construction', request, None, {})
#    prog = prog[0]
#    clas = list(prog.class_set.all().order_by('category'))
#    p = one + " " + two
#    return render_to_response('program/catalogue', request, prog,{'courses': clas })


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

    return render_to_response('display/qsd_listing.html', request, GetNode('Q/Web'), {'qsd_pages': qsd_pages, 'have_create': have_create })

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

    return render_to_response('display/qsd_listing.html', request, program, {'qsd_pages': qsd_pages,
                                                            'have_create': have_create })

def manage_programs(request):
    if not request.user or not request.user.isAdmin():
        raise Http404

    admPrograms = ESPUser(request.user).getEditable(Program).order_by('-id')

    return render_to_response('program/manage_programs.html', request, GetNode('Q/Web/myesp'), {'admPrograms': admPrograms})


@login_required
def managepage(request, page):
    if page == 'programs':
        return manage_programs(request)

    if page == 'newprogram':

        template_prog = None

	if 'template_prog' in request.GET:
            #try:
            tprogram = Program.objects.get(id=int(request.GET["template_prog"]))

            template_prog = {}
            template_prog.update(tprogram.__dict__)
            del template_prog["id"]
            
            template_prog["program_modules"] = tprogram.program_modules.all().values_list("id", flat=True)
            template_prog["class_categories"] = tprogram.class_categories.all().values_list("id", flat=True)
            template_prog["term"] = tprogram.anchor.name
            template_prog["term_friendly"] = tprogram.anchor.friendly_name
            template_prog["anchor"] = tprogram.anchor.parent.id
            
            # aseering 5/18/2008 -- List everyone who was granted V/Administer on the specified program
            template_prog["admins"] = User.objects.filter(userbit__verb=GetNode("V/Administer"), userbit__qsc=tprogram.anchor).values_list("id", flat=True)

            # aseering 5/18/2008 -- More aggressively list everyone who was an Admin
            #template_prog["admins"] = [ x.id for x in UserBit.objects.bits_get_users(verb=GetNode("V/Administer"), qsc=tprogram.anchor, user_objs=True) ]
            
            program_visible_bits = list(UserBit.objects.bits_get_users(verb=GetNode("V/Flags/Public"), qsc=tprogram.anchor).filter(user__isnull=True).order_by("-startdate"))
            if len(program_visible_bits) > 0:
                newest_bit = program_visible_bits[0]
                oldest_bit = program_visible_bits[-1]
    
                template_prog["publish_start"] = oldest_bit.startdate
                template_prog["publish_end"] = newest_bit.enddate

            student_reg_bits = list(UserBit.objects.bits_get_users(verb=GetNode("V/Deadline/Registration/Student"), qsc=tprogram.anchor).filter(user__isnull=True).order_by("-startdate"))
            if len(student_reg_bits) > 0:
                newest_bit = student_reg_bits[0]
                oldest_bit = student_reg_bits[-1]
    
                template_prog["student_reg_start"] = oldest_bit.startdate
                template_prog["student_reg_end"] = newest_bit.enddate

            teacher_reg_bits = list(UserBit.objects.bits_get_users(verb=GetNode("V/Deadline/Registration/Teacher"), qsc=tprogram.anchor).filter(user__isnull=True).order_by("-startdate"))
            if len(teacher_reg_bits) > 0:
                newest_bit = teacher_reg_bits[0]
                oldest_bit = teacher_reg_bits[-1]
    
                template_prog["teacher_reg_start"] = oldest_bit.startdate
                template_prog["teacher_reg_end"] = newest_bit.enddate

            
            line_items = LineItemType.objects.filter(anchor__name="Required", anchor__parent__parent=tprogram.anchor).values("amount", "finaid_amount")

            template_prog["base_cost"] = int(-sum([ x["amount"] for x in line_items]))
            template_prog["finaid_cost"] = int(-sum([ x["finaid_amount"] for x in line_items ]))

        if 'checked' in request.GET:
            # Our form's anchor is wrong, because the form asks for the parent of the anchor that we really want.
            # Don't bother trying to fix the form; just re-set the anchor when we're done.
            context = pickle.loads(request.session['context_str'])
            pcf = ProgramCreationForm(context['prog_form_raw'])
            if pcf.is_valid():
                new_prog = pcf.save(commit = False) # don't save, we need to fix it up:
                new_prog.anchor = GetNode(pcf.cleaned_data['anchor'].uri + "/" + pcf.cleaned_data["term"])
                new_prog.save()
                pcf.save_m2m()
                
                commit_program(new_prog, context['datatrees'], context['userbits'], context['modules'], context['costs'])
                
                manage_url = '/manage/' + new_prog.url() + '/resources'
                return HttpResponseRedirect(manage_url)
            else:
                raise ESPError(False), "Improper form data submitted."
              
    
        #   If the form has been submitted, process it.
        if request.method == 'POST':
            form = ProgramCreationForm(request.POST)
    
            if form.is_valid():
                temp_prog = form.save(commit=False)
                datatrees, userbits, modules = prepare_program(temp_prog, form)
                #   Save the form's raw data instead of the form itself, or its clean data.
                #   Unpacking of the data happens at the next step.

                context_pickled = pickle.dumps({'prog_form_raw': form.data, 'datatrees': datatrees, 'userbits': userbits, 'modules': modules, 'costs': ( form.cleaned_data['base_cost'], form.cleaned_data['finaid_cost'] )})
                request.session['context_str'] = context_pickled
                
                return render_to_response('program/newprogram_review.html', request, GetNode('Q/Programs/'), {'prog': temp_prog, 'datatrees': datatrees, 'userbits': userbits, 'modules': modules})
            
        else:
            #   Otherwise, the default view is a blank form.
            if template_prog:
                form = ProgramCreationForm(template_prog)
            else:
                form = ProgramCreationForm()

        return render_to_response('program/newprogram.html', request, GetNode('Q/Programs/'), {'form': form, 'programs': Program.objects.all().order_by('-id')})
        
    if page == 'submit_transaction':
        #   We might also need to forward post variables to http://shopmitprd.mit.edu/controller/index.php?action=log_transaction
        
        if request.POST.has_key("decision") and request.POST["decision"] != "REJECT":

            try:
                from decimal import Decimal
                post_locator = request.POST['merchantDefinedData1']
                post_amount = Decimal(request.POST['orderAmount'])
                post_id = request.POST['requestID']
                
                document = Document.receive_creditcard(request.user, post_locator, post_amount, post_id)
            except CompletedTransactionException:
                from django.conf import settings
                # Send e-mail notification of duplicate postback.
                invoice = Document.get_by_locator(post_locator)
                send_mail('[ ESP CC ] Duplicate Postback for #' + post_locator + ' by ' + invoice.user.first_name + ' ' + invoice.user.last_name, \
                      """Duplicate Postback Notification\n--------------------------------- \n\nDocument: %s\n\nUser: %s %s (%s)\n\nProgram anchor: %s\n\nRequest: %s\n\n""" % \
                      (invoice.locator, invoice.user.first_name, invoice.user.last_name, invoice.user.id, invoice.anchor.uri, request) , \
                      settings.SERVER_EMAIL, \
                      [contact[1] for contact in settings.ADMINS], True)
                # Get the document that would've been created instead
                document = invoice.docs_next.all()[0]
            except:
                raise ESPError(), "Your credit card transaction was successful, but a server error occurred while logging it.  The transaction has not been lost (please do not try to pay again!); this just means that the green Credit Card checkbox on the registration page may not be checked off.  Please <a href=\"mailto:esp-webmasters@mit.edu\">e-mail us</a> and ask us to correct this manually.  We apologize for the inconvenience."

            one = document.anchor.parent.name
            two = document.anchor.name

            return HttpResponseRedirect("http://%s/learn/%s/%s/confirmreg" % (request.META['HTTP_HOST'], one, two))
            
        return render_to_response( 'accounting_docs/credit_rejected.html', request, GetNode('Q/Accounting'), {} )

    #   QSD management
    if page == 'pages':
        if request.method == 'POST':
            data = request.POST
            if request.GET['cmd'] == 'bulk_move':
                if data.has_key('confirm'):
                    form = QSDBulkMoveForm(data)
                    #   Handle submission of bulk move form
                    if form.is_valid():
                        form.save_data()
                        return HttpResponseRedirect('/manage/pages')

                #   Create and display the form
                qsd_id_list = []
                for key in data.keys():
                    if key.startswith('check_'):
                        qsd_id_list.append(int(key[6:]))
                if len(qsd_id_list) > 0:
                    form = QSDBulkMoveForm()
                    qsd_list = QuasiStaticData.objects.filter(id__in=qsd_id_list)
                    anchor = form.load_data(qsd_list)
                    if anchor:
                        return render_to_response('qsd/bulk_move.html', request, DataTree.get_by_uri('Q/Web'), {'common_anchor': anchor, 'qsd_list': qsd_list, 'form': form})
            
            qsd = QuasiStaticData.objects.get(id=request.GET['id'])
            if request.GET['cmd'] == 'move':
                #   Handle submission of move form
                form = QSDMoveForm(data)
                if form.is_valid():
                    form.save_data()
                else:
                    return render_to_response('qsd/move.html', request, DataTree.get_by_uri('Q/Web'), {'qsd': qsd, 'form': form})
            elif request.GET['cmd'] == 'delete':
                #   Mark as inactive all QSD pages matching the one with ID request.GET['id']
                if data['sure'] == 'True':
                    all_qsds = QuasiStaticData.objects.filter(path=qsd.path, name=qsd.name)
                    for q in all_qsds:
                        q.disabled = True
                        q.save()
            return HttpResponseRedirect('/manage/pages')

        elif request.GET.has_key('cmd'):
            qsd = QuasiStaticData.objects.get(id=request.GET['id'])
            if request.GET['cmd'] == 'delete':
                #   Show confirmation of deletion
                return render_to_response('qsd/delete_confirm.html', request, DataTree.get_by_uri('Q/Web'), {'qsd': qsd})
            elif request.GET['cmd'] == 'undelete':
                #   Make all the QSDs enabled and return to viewing the list
                all_qsds = QuasiStaticData.objects.filter(path=qsd.path, name=qsd.name)
                for q in all_qsds:
                    q.disabled = False
                    q.save()
            elif request.GET['cmd'] == 'move':
                #   Show move form
                form = QSDMoveForm()
                form.load_data(qsd)
                return render_to_response('qsd/move.html', request, DataTree.get_by_uri('Q/Web'), {'qsd': qsd, 'form': form})
                
        #   Show QSD listing 
        qsd_list = []
        qsds = QuasiStaticData.objects.all().order_by('-create_date')
        url_list = []
        for qsd in qsds:
            url = qsd.url()
            if url not in url_list:
                qsd_list.append(qsd)
                url_list.append(url)
        qsd_list.sort(key=lambda q: q.url())
        return render_to_response('qsd/list.html', request, DataTree.get_by_uri('Q/Web'), {'qsd_list': qsd_list})

    raise Http404
