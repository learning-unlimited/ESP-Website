
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

from esp.membership.forms import ContactInfoForm, AlumniContactForm, AlumniRSVPForm
from esp.web.util.main import render_to_response
from django.core.mail import send_mail
from django.template import loader
from django.http import HttpResponseRedirect

# model dependencies
from esp.membership.models import AlumniContact, AlumniRSVP
from esp.users.models import ContactInfo
from esp.utils.forms import save_instance

def alumniform(request):
    """
    This view should take the form, send an e-mail to the right people and save the data in our database.
    """

    #  If it's a success, return success page
    if 'success' in request.GET:
        return render_to_response('membership/alumniform_success.html', request, request.get_node('Q/Web/about'), {})

    #   If the form has been submitted, process it.
    if request.method == 'POST':
        data = request.POST.copy()
        form1 = ContactInfoForm(data)
        form2 = AlumniContactForm(data)

        if form1.is_valid() and form2.is_valid():
            #   Save the information in the database
            new_contact = ContactInfo()
            new_info = AlumniContact()
            save_instance(form1, new_contact)
            save_instance(form2, new_info, {'contactinfo_id': new_contact.id}, True)
            
            #   Send an e-mail to esp-membership with details.
            SUBJECT_PREPEND = '[ESP Alumni] Contact From:'
            to_email = ['esp-50th-contact@esp.mit.edu']
            from_email = 'alumniform@esp.mit.edu'
            
            t = loader.get_template('email/alumniform')
    
            msgtext = t.render({'contact_form': form1, 'main_form': form2})
                    
            send_mail(SUBJECT_PREPEND + ' '+ form1.clean_data['first_name'] + ' ' + form1.clean_data['last_name'],
                    msgtext, from_email, to_email, fail_silently = True)
    
            return HttpResponseRedirect(request.path + '?success=1')

    else:
        #   Otherwise, the default view is a blank form.
        form1 = ContactInfoForm()
        form2 = AlumniContactForm()
    
    
    return render_to_response('membership/alumniform.html', request, request.get_node('Q/Web/about'), {'contact_form': form1, 'main_form': form2})

def alumnirsvp(request):
    """
    This view should take the form, send an e-mail to the right people and save the data in our database.
    """

    #  If it's a success, return success page
    if 'success' in request.GET:
        return render_to_response('membership/alumniform_success.html', request, request.get_node('Q/Web/about'), {})

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
            to_email = ['esp-50th-contact@esp.mit.edu']
            from_email = 'alumnirsvp@esp.mit.edu'
            
            t = loader.get_template('email/alumnirsvp')
    
            msgtext = t.render({'form': form})
                    
            send_mail(SUBJECT_PREPEND + ' '+ form.clean_data['name'], msgtext, from_email, to_email, fail_silently = True)
    
            return HttpResponseRedirect(request.path + '?success=1')

    else:
        #   Otherwise, the default view is a blank form.
        form = AlumniRSVPForm()
    
    return render_to_response('membership/alumnirsvp.html', request, request.get_node('Q/Web/about'), {'form': form})

