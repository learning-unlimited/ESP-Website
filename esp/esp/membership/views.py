
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

from esp.membership.models import *
from esp.web.util.main import render_to_response
from esp.datatree.models import DataTree, GetNode
from django.core.mail import send_mail
from django.template import loader
from django.http import HttpResponseRedirect

def save_instance(form, instance, additional_fields={}, commit=True):
    """
    Saves bound Form ``form``'s clean_data into model instance ``instance``.

    Assumes ``form`` has a field for every non-AutoField database field in
    ``instance``. If commit=True, then the changes to ``instance`` will be
    saved to the database. Returns ``instance``.
    
    Modified to override missing form keys (fields removed by formfield_callback)
    """
    from django.db import models
    opts = instance.__class__._meta
    
    if form.errors:
        raise ValueError("The %s could not be changed because the data didn't validate." % opts.object_name)
    clean_data = form.clean_data
    
    for f in opts.fields:
        if not f.editable or isinstance(f, models.AutoField):
            continue
        if f.name in clean_data.keys():
            setattr(instance, f.name, clean_data[f.name])
        
    #   If additional fields are supplied, write them into the instance.
    #   I don't have a better way right now.
    for fname in additional_fields.keys():
            setattr(instance, fname, additional_fields[fname])
            
    if commit:
        instance.save()
        for f in opts.many_to_many:
            if f.name in clean_data.keys():
                setattr(instance, f.attname, clean_data[f.name])

    # GOTCHA: If many-to-many data is given and commit=False, the many-to-many
    # data will be lost. This happens because a many-to-many options cannot be
    # set on an object until after it's saved. Maybe we should raise an
    # exception in that case.
    return instance

def alumniform(request):
    """
    This view should take the form, send an e-mail to the right people and save the data in our database.
    """
    
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
            to_email = ['esp-membership@mit.edu']
            from_email = 'alumniform@esp.mit.edu'
            
            t = loader.get_template('email/alumniform')
    
            msgtext = t.render({'contact_form': form1, 'main_form': form2})
                    
            send_mail(SUBJECT_PREPEND + ' '+ form1.clean_data['first_name'] + ' ' + form1.clean_data['last_name'],
                    msgtext, from_email, to_email, fail_silently = True)
    
            return render_to_response('membership/alumniform_success.html', request, GetNode('Q/Web/about'), {'message': msgtext})

    #   Otherwise, the default view is a blank form.
    form1 = ContactInfoForm()
    form2 = AlumniContactForm()
    
    #   Set additional formatting attributes for the fields in those forms.
    form1.fields['address_city'].line_group = 0
    form1.fields['address_state'].line_group = 0
    form1.fields['address_zip'].line_group = 0
    form1.fields['phone_day'].line_group = 1
    form1.fields['phone_even'].line_group = 1
    form1.fields['phone_cell'].line_group = 1
    form2.fields['comments'].is_long = True
    
    return render_to_response('membership/alumniform.html', request, GetNode('Q/Web/about'), {'contact_form': form1, 'main_form': form2})

