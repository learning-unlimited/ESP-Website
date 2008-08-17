
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

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

from esp.membership.forms import ContactInfoForm, AlumniInfoForm, AlumniContactForm, AlumniRSVPForm, AlumniLookupForm, AlumniMessageForm
from esp.datatree.models import DataTree
from esp.qsd.models import QuasiStaticData
from esp.web.util.main import render_to_response
from django.core.mail import send_mail
from django.template import loader
from django.http import HttpResponseRedirect

# model dependencies
from esp.membership.models import AlumniInfo, AlumniRSVP, AlumniContact, AlumniMessage
from esp.users.models import ContactInfo
from esp.utils.forms import save_instance

from esp.middleware import ESPError

def alumnihome(request):
    """
    Main page for alumni.  Shows current discussions and all QSD pages in Q/Web/alumni.
    """
    context = {}
    
    context['links'] = QuasiStaticData.objects.filter(path=DataTree.get_by_uri('Q/Web/alumni'))
    context['threads'] = AlumniContact.objects.all()
    
    return render_to_response('membership/alumnihome.html', request, request.get_node('Q/Web/alumni'), context)

def thread(request, extra):
    
    context = {}
    
    if request.GET.has_key('success'):
        context['success'] = True
    
    threads = AlumniContact.objects.filter(id=extra)
    if threads.count() == 1:
        thread = threads[0]
        context['thread'] = thread
        
    if request.method == 'POST':
        #   Handle submission of replies.
        data = request.POST.copy()
        form = AlumniMessageForm(thread, data, request=request)
        try:
            if form.is_valid():
                new_message = AlumniMessage()
                new_message.thread = thread
                del form.cleaned_data['thread']
                save_instance(form, new_message, commit=False)
                new_message.save()
                return HttpResponseRedirect(request.path + '?success=1')
        except UnicodeDecodeError:
            raise ESPError(False), "You have entered a comment containing invalid international characters.  If you are entering international characters, please make sure your browser uses the Unicode UTF-8 text format to do so."

    return render_to_response('membership/thread_view.html', request, request.get_node('Q/Web/alumni'), context)

def alumnicontact(request):
    """
    Contact form for alumni.  A discussion thread can be associated with a
    particular program or event from a particular year.  Each thread also
    has one or more alumni associated with it.  Each update is e-mailed to
    esp-membership and the associated alumni.
    """
    context = {}
    
    context['form'] = AlumniContactForm(request=request)
    context['threads'] = AlumniContact.objects.all()
    
    if request.GET.has_key('success'):
        context['success'] = True
        
    if request.method == 'POST':
        data = request.POST.copy()
        form = AlumniContactForm(data, request=request)
        if form.is_valid():
            new_contact = form.load_data()
            return HttpResponseRedirect('/alumni/thread/%d' % new_contact.id)
        else:
            context['form'] = form
    
    return render_to_response('membership/alumnicontact.html', request, request.get_node('Q/Web/alumni'), context)

def alumnilookup(request):
    """
    Provide a page where someone can look up ESP users and alumni:
    -   search by name or year range
    -   show stories
    -   enter theirs or someone else's contact information
    """
    context = {}
    #   Usually, the default view is a blank form.
    context['contact_form'] = ContactInfoForm()
    context['lookup_form'] = AlumniLookupForm()
    context['info_form'] = AlumniInfoForm(request=request)
    
    #   If successful, display the appropriate message from the template.
    if request.GET.has_key('success'):
        context['success'] = True
    
    #   If the form has been submitted, process it.
    if request.method == 'POST':
        data = request.POST.copy()
        
        #   Option 1: submitted information for someone.
        method = data.get('method', 'none')
        if method == 'submit':
            
            form1 = ContactInfoForm(data)
            form2 = AlumniInfoForm(data, request=request)
    
            if form2.is_valid() and form1.is_valid():
                #   Save the information in the database
                new_info = AlumniInfo()
                
                #   Contact info form does additional check to see if making a new one is really necessary
                new_contact = form1.load_user()
                
                #   Delete previous instances of this person.
                AlumniInfo.objects.filter(contactinfo__last_name=new_contact.last_name, contactinfo__first_name=new_contact.first_name).delete()
                save_instance(form2, new_info, {'contactinfo_id': new_contact.id}, True)
                
                #   Send an e-mail to esp-membership with details.
                SUBJECT_PREPEND = '[ESP Alumni] Information Submitted:'
                to_email = ['esp-membership@mit.edu']
                from_email = 'alumniform@esp.mit.edu'
                
                t = loader.get_template('email/alumniinfo')
        
                msgtext = t.render({'contact_form': form1, 'main_form': form2})
                        
                send_mail(SUBJECT_PREPEND + ' '+ form1.cleaned_data['first_name'] + ' ' + form1.cleaned_data['last_name'],
                        msgtext, from_email, to_email, fail_silently = True)
        
                return HttpResponseRedirect(request.path + '?success=1')
            else:
                #   Hand back the form if it has errors.
                context['contact_form'] = form1
                context['info_form'] = form2
            
        elif method == 'lookup':
            form = AlumniLookupForm(data)
            if form.is_valid():
                #   Find the user requested.
                alumni_list = AlumniInfo.lookup(form.cleaned_data)
                #   Populate the context for the page with links to enter more information.
                context['lookup_performed'] = True
                context['lookup_list'] = list(alumni_list)
            else:
                #   Hand back the form if it has errors.
                context['lookup_form'] = form

    
    return render_to_response('membership/alumnilookup.html', request, request.get_node('Q/Web/alumni'), context)

def alumnirsvp(request):
    """
    This view should take the form, send an e-mail to the right people and save the data in our database.
    """

    #  If it's a success, return success page
    if 'success' in request.GET:
        return render_to_response('membership/alumniform_success.html', request, request.get_node('Q/Web/alumni'), {})

    #   If the form has been submitted, process it.
    if request.method == 'POST':
        data = request.POST.copy()
        form = AlumniRSVPForm(data)

        if form.is_valid():
            #   Save the information in the database
            new_rsvp = AlumniRSVP()
            save_instance(form, new_rsvp)
            
            #   Send an e-mail to esp-membership with details.
            SUBJECT_PREPEND = '[ESP Alumni] RSVP From:'
            to_email = ['esp-membership@mit.edu']
            from_email = 'alumnirsvp@esp.mit.edu'
            
            t = loader.get_template('email/alumnirsvp')
    
            msgtext = t.render({'form': form})
                    
            send_mail(SUBJECT_PREPEND + ' '+ form.cleaned_data['name'], msgtext, from_email, to_email, fail_silently = True)
    
            return HttpResponseRedirect(request.path + '?success=1')

    else:
        #   Otherwise, the default view is a blank form.
        form = AlumniRSVPForm()
    
    return render_to_response('membership/alumnirsvp.html', request, request.get_node('Q/Web/alumni'), {'form': form})

