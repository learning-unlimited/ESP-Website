
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
  Email: web-team@learningu.org
"""
""" This module will render latex code and return a rendered display. """

import os.path
import os
from subprocess import check_call, STDOUT
from random import random
from functools import partial
import hashlib
import tempfile
from esp.middleware import ESPError
from django.http import HttpResponse

TEX_TEMP = tempfile.gettempdir()
TEX_EXT  = '.tex'
_devnull_sentinel = object()

def render_to_latex(filepath, context_dict=None, filetype='pdf'):
    """ Render some tex source to latex. This will run the latex
        interpreter and generate the necessary file type
        (either pdf, tex, ps, dvi, or a log file)   """
    from django.template import Context, Template, loader ## aseering 8-19-2010: Yes, this should be Context, not RequestContext
    from django.conf import settings

    if context_dict is None: context_dict = {}

    if isinstance(filepath, Template):
        t = filepath
    elif isinstance(filepath, (tuple, list)):
        t = loader.select_template(filepath)
    else:
        t = loader.get_template(filepath)
    
    context = Context(context_dict)

    context['MEDIA_ROOT'] = settings.MEDIA_ROOT
    context['file_type'] = filetype

    rendered_source = t.render(context)
    
    return gen_latex(rendered_source, filetype)

def gen_latex(texcode, type='pdf', remove_files=False, stdout=_devnull_sentinel, stderr=STDOUT):
    """Generate the latex code.

    :param texcode:
        The latex source code to use to generate the output.
    :type texcode:
        `unicode`
    :param type:
        The type of file to generate.
        Must be one of 'pdf', 'tex', 'log', 'svg', or 'png'.
        'tex' returns texcode itself, without processing.
        'log' returns the log file from the execution of latex on texcode.
        The others return the compilation of texcode into that format.
    :type type:
        `str`, element of ('pdf', 'tex', 'log', 'svg', 'png')
    :param remove_files:
        True if intermediate build files should be removed, else False.
    :type remove_files:
        `bool`
    :param stdout:
        See subprocess.__doc__.
        Default is to redirect to os.devnull, which does not print output to stdout.
    :type stdout:
        `int` or `file` or `None`
    :param stderr:
        See subprocess.__doc__.
        Default is STDOUT, which directs output to the same place that is
        specified by the stdout param.
    :type stderr:
        `int` or `file` or `None`
    :return:
        The generated file.
    :rtype:
        HttpResponse
    """
    with open(os.devnull, 'w') as devnull_file:
        # NOTE(jmoldow): `_devnull_sentinel` is private, and currently only the
        # default parameter for `stdout` uses it, so this list comprehension
        # isn't necessary. But using the list comprehension means that the
        # right thing will happen if someone were to change the default
        # parameter for `stderr`.
        stdout, stderr = [devnull_file if f is _devnull_sentinel else f for f in [stdout, stderr]]

        return _gen_latex(texcode, stdout=stdout, stderr=stderr, type=type, remove_files=remove_files)


def _gen_latex(texcode, stdout, stderr, type='pdf', remove_files=False):
    file_base = os.path.join(TEX_TEMP, get_rand_file_base())

    if type == 'tex':
        return HttpResponse(texcode, mimetype='text/plain')

    # write to the LaTeX file
    with open(file_base+TEX_EXT, 'w') as texfile:
        texfile.write(texcode.encode('utf-8'))

    file_types = ['pdf','log','tex','svg','png']

    # Get (sometimes-)necessary library files
    from django.conf import settings
    import shutil
    
    #   Set latex options
    latex_options = ['-interaction', 'nonstopmode', '-halt-on-error']

    # All command calls will use the same values for the cwd, stdout, and
    # stderr arguments, so we define a partially-applied callable call()
    # that makes it easier to call check_call() with these values.
    call = partial(check_call, cwd=TEX_TEMP, stdout=stdout, stderr=stderr)

    if type == 'pdf':
        mime = 'application/pdf'
        call(['pdflatex'] + latex_options + ['%s.tex' % file_base])

    elif type == 'log':
        mime = 'text/plain'
        call(['latex'] + latex_options + ['%s.tex' % file_base])

    elif type == 'svg':
        mime = 'image/svg+xml'
        call(['pdflatex'] + latex_options + ['%s.tex' % file_base])
        call(['inkscape', '%s.pdf' % file_base, '-l', '%s.svg' % file_base])
        if remove_files:
            os.remove('%s.pdf' % file_base)

    elif type == 'png':
        mime = 'image/png'
        call(['pdflatex'] + latex_options + ['%s.tex' % file_base])
        call(['convert', '-density', '192',
              '%s.pdf' % file_base, '%s.png' % file_base])
        if remove_files:
            os.remove('%s.pdf' % file_base)

    else:
        raise ESPError('Invalid type received for latex generation: %s should be one of %s' % (type, file_types))
    
    
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
            if type is 'png' and not os.path.isfile(file_base+'.'+type):
                #If the schedule is multiple pages (such as a schedule if the program is using barcode check-in), ImageMagick will generate files of the form file_base-n.png.  In this case, we will just return the first page.  Most of the time, if we expect something multi-page, we won't use PNG anyway; this is mostly for the benefit of the schedule printing script.
                out_file = file_base + '-0.png'
            else:
                out_file = file_base + '.' + type
            new_file     = open(out_file, 'rb')
            new_contents = new_file.read()
            new_file.close()
            if remove_files:
                os.remove(out_file)
                os.remove(file_base+TEX_EXT)
        
        except:
            raise ESPError('Could not read contents of %s. (Hint: try looking at the log file)' % (file_base+'.'+type))

    if type=='log':
        new_contents = tex_log

    return HttpResponse(new_contents, mimetype=mime)

    
    

def get_rand_file_base():
    rand = hashlib.md5(str(random())).hexdigest()

    while os.path.exists(os.path.join(TEX_TEMP, rand+TEX_EXT)):
        rand = hashlib.md5(str(random())).hexdigest()

    return rand



    

