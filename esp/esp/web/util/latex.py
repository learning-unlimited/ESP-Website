
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
""" This module will render latex code and return a rendered display. """

import os.path
import os
from random import random
import hashlib
import tempfile
from esp.middleware import ESPError
from django.http import HttpResponse
import codecs

TEX_TEMP = tempfile.gettempdir()
TEX_EXT  = '.tex'

def render_to_latex(filepath, context_dict=None, filetype='pdf'):
    """ Render some tex source to latex. This will run the latex
        interpreter and generate the necessary file type
        (either pdf, tex, ps, dvi, or a log file)   """
    from django.template import Context, Template, loader
    from django.conf import settings

    if context_dict is None: context_dict = {}

    #   This is a hack to satisfy Django's requirement that the 'extends' tag come first.
    #   So, if you make a template, put the 'extends' tag in the first line.
    #   Especially if it's for Latex. :)
    src = loader.find_template_source(filepath)[0]
    src_lines = src.lstrip('\n').split('\n')
    src = src_lines[0] + '\n{% load latex %}' + '\n'.join(src_lines[1:])
    context = Context(context_dict)

    context['MEDIA_ROOT'] = settings.MEDIA_ROOT
    context['file_type'] = filetype

    t = Template(src)

    rendered_source = t.render(context)
    
    return gen_latex(rendered_source, filetype)
    

def gen_latex(texcode, type='pdf'):
    """ Generate the latex code. """

    remove_files = False
    file_base = os.path.join(TEX_TEMP, get_rand_file_base())

    if type == 'tex':
        return HttpResponse(texcode, mimetype='text/plain')
    

    # write to the LaTeX file
    texfile   = open(file_base+TEX_EXT, 'w')
    texfile.write(texcode.encode('utf-8'))
    texfile.close()
    

    file_types = ['pdf','dvi','ps','log','tex','svg','png']

    # Get (sometimes-)necessary library files
    from django.conf import settings
    import shutil
    shutil.copy( "%s/esp/3rdparty/pspicture.ps" % settings.PROJECT_ROOT, TEX_TEMP )
    
    if type=='pdf':
        mime = 'application/pdf'
        os.system('cd %s; latex %s.tex' % (TEX_TEMP, file_base))
        os.system('cd %s; dvips -t letter %s.dvi' % (TEX_TEMP, file_base))
        os.system('cd %s; ps2pdf %s.ps' % (TEX_TEMP, file_base))
        if remove_files:
            os.remove('%s.dvi' % file_base)
            os.remove('%s.ps' % file_base)
            
    elif type=='dvi':
        mime = 'application/x-dvi'
        os.system('cd %s; latex %s.tex' % (TEX_TEMP, file_base))
        
    elif type=='ps':
        mime = 'application/postscript'
        os.system('cd %s; latex %s.tex' % (TEX_TEMP, file_base))
        os.system('cd %s; dvips %s -o %s.ps' % (TEX_TEMP, file_base, file_base))
        if remove_files:
            os.remove('%s.dvi' % file_base)
        
    elif type=='log':
        mime = 'text/plain'
        os.system('cd %s; latex %s.tex' % (TEX_TEMP, file_base))

    elif type=='svg':
        mime = 'image/svg+xml'
        os.system('cd %s; pwd; latex %s.tex' % (TEX_TEMP, file_base))
        os.system('cd %s; dvips -t letter %s.dvi' % (TEX_TEMP, file_base))
        os.system('cd %s; ps2pdf %s.ps' % (TEX_TEMP, file_base))
        os.system('cd %s; inkscape %s.pdf -l %s.svg' % (TEX_TEMP, file_base, file_base))
        if remove_files:
            os.remove('%s.dvi' % file_base)
            os.remove('%s.ps' % file_base)
            os.remove('%s.pdf' % file_base)
        
    elif type=='png':
        mime = 'application/postscript'
        os.system('cd %s; latex %s.tex' % (TEX_TEMP, file_base))
        os.system('cd %s; dvips -t letter %s.dvi' % (TEX_TEMP, file_base))
        os.system('cd %s; convert %s.ps %s.png' % (TEX_TEMP, file_base, file_base))
        if remove_files:
            os.remove('%s.dvi' % file_base)
            os.remove('%s.ps' % file_base)

    else:
        raise ESPError(), 'Invalid type received for latex generation: %s should be one of %s' % (type, file_types)
    
    
    try:
        tex_log_file = open(file_base+'.log')
        tex_log      = tex_log_file.read()
        tex_log_file.close()
        if remove_files: 
            os.remove(file_base+'.log')
    except:
        tex_log      = ''

    if type != 'log':
        try:
            new_file     = open(file_base+'.'+type)
            new_contents = new_file.read()
            new_file.close()
            if remove_files:
                os.remove(file_base+'.'+type)
                os.remove(file_base+TEX_EXT)
        
        except:
            raise ESPError(), 'Could not read contents of %s. (Hint: try looking at the log file)' % (file_base+'.'+type)

    if type=='log':
        new_contents = tex_log

    return HttpResponse(new_contents, mimetype=mime)

    
    

def get_rand_file_base():
    rand = hashlib.md5(str(random())).hexdigest()

    while os.path.exists(os.path.join(TEX_TEMP, rand+TEX_EXT)):
        rand = hashlib.md5(str(random())).hexdigest()

    return rand



    

