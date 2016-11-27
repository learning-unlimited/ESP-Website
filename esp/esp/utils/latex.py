
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

import hashlib
import os.path
import os
from functools import partial
from random import random
import shutil
import subprocess
import tempfile

from django.conf import settings
from django.http import HttpResponse
from django.template import Template, loader

from esp.middleware import ESPError

TEX_TEMP = tempfile.gettempdir()
TEX_EXT  = '.tex'
_devnull_sentinel = object()

# File types that are valid outputs, and the corresponding response mimetypes
FILE_MIME_TYPES = {
    'pdf': 'application/pdf',
    'log': 'text/plain',
    'tex': 'text/plain',
    'svg': 'image/svg+xml',
    'png': 'image/png',
}


def render_to_latex(filepath, context_dict=None, filetype='pdf'):
    """Render some tex source to latex.
    
    This will run the latex interpreter and generate the necessary file type,
    which must be one of those from FILE_MIME_TYPES.
    """
    if filetype not in FILE_MIME_TYPES:
        raise ESPError('Invalid type received for latex generation: %s should '
                       'be one of %s' % (type, FILE_MIME_TYPES))

    if context_dict is None: context_dict = {}

    if isinstance(filepath, Template):
        t = filepath
    elif isinstance(filepath, (tuple, list)):
        t = loader.select_template(filepath)
    else:
        t = loader.get_template(filepath)

    context_dict['MEDIA_ROOT'] = settings.MEDIA_ROOT
    context_dict['file_type'] = filetype

    rendered_source = t.render(context_dict)

    contents = gen_latex(rendered_source, filetype)
    return HttpResponse(contents, content_type=FILE_MIME_TYPES[filetype])


def gen_latex(texcode, type='pdf', stdout=_devnull_sentinel, stderr=subprocess.STDOUT):
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
        The generated file contents.
    :rtype:
        `str`
    """
    with open(os.devnull, 'w') as devnull_file:
        # NOTE(jmoldow): `_devnull_sentinel` is private, and currently only the
        # default parameter for `stdout` uses it, so this list comprehension
        # isn't necessary. But using the list comprehension means that the
        # right thing will happen if someone were to change the default
        # parameter for `stderr`.
        stdout, stderr = [devnull_file if f is _devnull_sentinel else f for f in [stdout, stderr]]

        return _gen_latex(texcode, stdout=stdout, stderr=stderr, type=type)


def _gen_latex(texcode, stdout, stderr, type='pdf'):
    file_base = os.path.join(TEX_TEMP, get_rand_file_base())

    if type == 'tex':
        return texcode

    # write to the LaTeX file
    with open(file_base+TEX_EXT, 'w') as texfile:
        texfile.write(texcode.encode('utf-8'))

    #   Set latex options
    latex_options = ['-interaction', 'nonstopmode', '-halt-on-error']

    # All command calls will use the same values for the cwd, stdout, and
    # stderr arguments, so we define a partially-applied callable check_call()
    # that makes it easier to call subprocess.check_call() with these values
    # (and similarly for call()).
    check_call = partial(subprocess.check_call, cwd=TEX_TEMP, stdout=stdout, stderr=stderr)
    call = partial(subprocess.call, cwd=TEX_TEMP, stdout=stdout, stderr=stderr)

    retcode = call(['pdflatex'] + latex_options + ['%s.tex' % file_base])
    try:
        with open('%s.log' % file_base) as f:
            tex_log = f.read()
    except Exception as e:
        raise ESPError('Could not read log file; something has gone horribly '
                       'wrong.  Error details: %s' % e)

    if type == 'log':
        # If we're getting the log, an error is fine -- we're probably trying
        # to debug one!
        return tex_log
    elif retcode:
        # Otherwise, if there was an error, we want to exit now since things
        # didn't work.
        # TODO(benkraft): Return part of the log file here.
        raise ESPError("LaTeX failed; try looking at the log file.")


    if type == 'svg':
        check_call(['inkscape', '%s.pdf' % file_base, '-l', '%s.svg' % file_base])
    elif type == 'png':
        check_call(['convert', '-density', '192',
              '%s.pdf' % file_base, '%s.png' % file_base])


    try:
        if type is 'png' and not os.path.isfile(file_base+'.'+type):
            #If the schedule is multiple pages (such as a schedule if the program is using barcode check-in), ImageMagick will generate files of the form file_base-n.png.  In this case, we will just return the first page.  Most of the time, if we expect something multi-page, we won't use PNG anyway; this is mostly for the benefit of the schedule printing script.
            out_file = file_base + '-0.png'
        else:
            out_file = file_base + '.' + type
        new_file     = open(out_file, 'rb')
        new_contents = new_file.read()
        new_file.close()

    except:
        raise ESPError('Could not read contents of %s. (Hint: try looking at the log file)' % (file_base+'.'+type))

    return new_contents




def get_rand_file_base():
    rand = hashlib.md5(str(random())).hexdigest()

    while os.path.exists(os.path.join(TEX_TEMP, rand+TEX_EXT)):
        rand = hashlib.md5(str(random())).hexdigest()

    return rand





