
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
import subprocess
import tempfile

from django.conf import settings
from django.http import HttpResponse
from django.template import Template, loader

from esp.middleware import ESPError

TEX_TEMP = tempfile.gettempdir()
TEX_EXT  = '.tex'
_devnull_sentinel = object()
LATEX_OPTIONS = ['-interaction', 'nonstopmode', '-halt-on-error']

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
                       'be one of %s' % (filetype, ', '.join(FILE_MIME_TYPES)))

    context_dict = context_dict or {}

    if isinstance(filepath, Template):
        t = filepath
    elif isinstance(filepath, (tuple, list)):
        t = loader.select_template(filepath)
    else:
        t = loader.get_template(filepath)

    context_dict['MEDIA_ROOT'] = settings.MEDIA_ROOT
    context_dict['file_type'] = filetype
    context_dict['settings'] = settings

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

    # All command calls will use the same values for the cwd, stdout, and
    # stderr arguments, so we define a partially-applied callable call() that
    # makes it easier to call subprocess.call() with these values.
    call = partial(subprocess.call, cwd=TEX_TEMP, stdout=stdout, stderr=stderr)

    retcode = call(['pdflatex'] + LATEX_OPTIONS + ['%s.tex' % file_base])

    try:
        with open('%s.log' % file_base) as f:
            tex_log = f.read()
    except Exception as e:
        # In this case, there's not much to do except error -- pdflatex will
        # always write a log if it succeeds, or even if it fails due to bad
        # code or for almost any other reason.
        # TODO(benkraft): We could also return the stdout of the process,
        # although it's a little tricky since we have to make sure to buffer
        # the pipe correctly -- see c42bd1b9.
        raise ESPError('Could not read log file; something has gone horribly '
                       'wrong.  Error details: %s' % e)

    if type == 'log':
        # If we're getting the log, an error is fine -- we're probably trying
        # to debug one!
        return tex_log
    elif retcode:
        # Otherwise, if there was an error, we want to exit now since things
        # didn't work.
        # TODO(benkraft): Try to extract the actual error out of pdflatex's
        # various output.  Or use stdout, which is a bit less noisy.
        raise ESPError('LaTeX failed with code %s; try looking at the log '
                       'file.  Here are '
                       'the last 1000 characters of the log: %s'
                       % (retcode, tex_log[-1000:]))
    elif 'No pages of output' in tex_log:
        # One common problem (which LaTeX doesn't treat as an error) is
        # selecting no students, which results in no output (thus a nonexistent
        # file, and an error converting or reading it later).  We'll just exit
        # right here in that case.
        raise ESPError('LaTeX generated no output.  Are you sure you selected '
                       'any users?')

    if type == 'svg':
        retcode = call(['inkscape', '%s.pdf' % file_base, '-l',
                        '%s.svg' % file_base])
    elif type == 'png':
        retcode = call(['convert', '-density', '192', '%s.pdf' % file_base,
                        '%s.png' % file_base])

    if retcode:
        raise ESPError("Postprocessing failed; try downloading as PDF.")

    out_file = file_base + '.' + type
    if type is 'png' and not os.path.isfile(out_file):
        # If the schedule is multiple pages (such as a schedule if the program
        # is using barcode check-in), ImageMagick will generate files of the
        # form file_base-n.png.  In this case, we will just return the first
        # page.  Most of the time, if we expect something multi-page, we won't
        # use PNG anyway; this is mostly for the benefit of the schedule
        # printing script.
        out_file = file_base + '-0.png'
    if not os.path.isfile(out_file):
        # We probably shouldn't get here -- this means either LaTeX failed,
        # LaTeX generated no output, or a postprocessor failed, all of which we
        # handle above.  But we'll at least return a specific error.
        raise ESPError('No output file %s found; try looking at the log '
                       'file.' % out_file)
    with open(out_file) as f:
        return f.read()


def get_rand_file_base():
    rand = hashlib.md5(str(random())).hexdigest()

    while os.path.exists(os.path.join(TEX_TEMP, rand+TEX_EXT)):
        rand = hashlib.md5(str(random())).hexdigest()

    return rand
