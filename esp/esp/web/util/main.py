
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""
from esp.users.models import ESPUser
from django.template import Context, Template, loader, RequestContext
from django.conf import settings
from django import http
from django.http import HttpResponse
from django.contrib.auth.models import AnonymousUser
from esp.program.models import Program
from esp.qsd.models import ESPQuotations
from esp.middleware import ESPError
from django.conf import settings
import django.shortcuts

def get_from_id(id, module, strtype = 'object', error = True):
    """ This function will get an object from its id, and return an appropriate error if need be. """
    from esp.users.models import ESPUser

    try:
        newid    = int(id)
        foundobj = module.objects.get(id = newid)
        if module == ESPUser:
            foundobj = ESPUser(foundobj)
    except:
        if error:
            raise ESPError(False), 'Could not find the %s with id %s.' % (strtype, id)
        return None
    return foundobj
    
def render_response(request, template, dictionary, mimetype=None, ):
    from esp.web.util.idebug import idebug_hook
    inst = RequestContext(request)
    inst.update(dictionary)
    idebug_hook(request, inst)
    
    return django.shortcuts.render_to_response(template, {}, context_instance = inst, mimetype=mimetype, )

def _per_program_template_name(prog, templatename):
    tpath = templatename.split("/")
    new_tpath = tpath[:-1] + ["per_program", "%s_%s" % (prog.id, tpath[-1])]
    return "/".join(new_tpath)

def render_to_response(template, requestOrContext, prog = None, context = None, auto_per_program_templates = True, mimetype=None, use_request_context=True):
    from esp.web.views.navBar import makeNavBar

    if isinstance(template, (basestring,)):
        template = [ template ]

    if isinstance(prog, (list, tuple)) and auto_per_program_templates:
        template = [_per_program_template_name(prog[0], t) for t in template] + template

    # if there are only two arguments
    if context is None and prog is None:
        context = {'navbar_list': []}
        context['DEFAULT_EMAIL_ADDRESSES'] = settings.DEFAULT_EMAIL_ADDRESSES
        context['EMAIL_HOST'] = settings.EMAIL_HOST
        return django.shortcuts.render_to_response(template, requestOrContext, Context(context), mimetype=mimetype)
    
    if context is not None:
        request = requestOrContext

        section = ''

        if type(prog) == tuple:
            section = prog[1]
            prog = prog[0]
            
        #   Add e-mail addresses
        context['DEFAULT_EMAIL_ADDRESSES'] = settings.DEFAULT_EMAIL_ADDRESSES
        context['EMAIL_HOST'] = settings.EMAIL_HOST

        if not context.has_key('program'):
            if type(prog) == Program:
                context['program'] = prog
                
        # create nav bar list
        if not context.has_key('navbar_list'):
            category = None
            if context.has_key('nav_category'):
                category = context['nav_category']
            if prog is None:
                context['navbar_list'] = []
            elif type(prog) == Program:
                context['navbar_list'] = makeNavBar(AnonymousUser(), prog.anchor, section, category)
            else:
                context['navbar_list'] = makeNavBar(AnonymousUser(), prog, section, category)

        #   Force comprehension of navbar list
        if hasattr(context['navbar_list'], 'value'):
            context['navbar_list'] = context['navbar_list'].value
        
        if not use_request_context:
            context['request'] = request
            response = django.shortcuts.render_to_response(template, context, mimetype=mimetype)
            return response
        else:
            return render_response(request, template, context, mimetype=mimetype)
        
    assert False, 'render_to_response expects 2 or 4 arguments.'

""" Override Django error views to provide some context info. """
def error404(request, template_name='404.html'):
    context = {'request_path': request.path}
    context['DEFAULT_EMAIL_ADDRESSES'] = settings.DEFAULT_EMAIL_ADDRESSES
    context['EMAIL_HOST'] = settings.EMAIL_HOST
    t = loader.get_template(template_name) # You need to create a 404.html template.
    return http.HttpResponseNotFound(t.render(RequestContext(request, context)))

def error500(request, template_name='500.html'):
    context = {}
    context['DEFAULT_EMAIL_ADDRESSES'] = settings.DEFAULT_EMAIL_ADDRESSES
    context['EMAIL_HOST'] = settings.EMAIL_HOST
    context['request'] = request
    t = loader.get_template(template_name) # You need to create a 500.html template.
    return http.HttpResponseServerError(t.render(Context(context)))
