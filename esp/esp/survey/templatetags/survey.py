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

from django import template
from django.http import QueryDict
from django.template import loader
from esp.program.models.class_ import ClassSubject


import os
import subprocess

try:
    import cPickle as pickle
except ImportError:
    import pickle

register = template.Library()

@register.filter
def midValue(sizeLs0):
    sizeLst = int(sizeLs0)
    if sizeLst%2 == 1:
        return ((sizeLst + 1) / 2 )
    else:
        return -1

@register.filter
def intrange(min_val, max_val):
    return range(int(min_val), int(max_val) + 1)

@register.filter
def field_width(min_val, max_val):
    return '%d%%' % (70 / (int(max_val) - int(min_val) + 1))

@register.filter
def substitute(input_str, item):
    #   Puts all of the attributes of the given item in the context dictionary
    t = template.Template(input_str)
    c = template.Context(item.__dict__)
    return t.render(c)

@register.filter
def uselist(input_str, lst):
    #   Takes a list of stuff and puts it in context as 'lst'
    t = template.Template(input_str)
    c = template.Context({'lst': lst})
    return t.render(c)

@register.filter
def unpack_answers(lst):
    # Pulls out actual, unpickled answers from a list of Answer objects
    return [x.answer for x in lst]

@register.filter
def drop_empty_answers(lst):
    #   Takes a list of answers and drops empty ones. Whitespace-only is empty.
    return [ ans for ans in lst if (not isinstance(ans.answer, basestring)) or ans.answer.strip() ]

@register.filter
def average(lst):
    if len(lst) == 0:
        return 'N/A'
    try:
        sum = 0.0
        for l in lst:
            sum += float(l)
        return str(round(sum / len(lst), 2))
    except:
        return 'N/A'

@register.filter
def stdev(lst):
    if len(lst) == 0:
        return 'N/A'
    try:
        sum = 0.0
        std_sum = 0.0
        for l in lst:
            sum += float(l)
        mean = sum / len(lst)
        for l in lst:
            std_sum += abs(float(l) - mean)
        return str(round(std_sum / len(lst), 2))
    except:
        return 'N/A'

@register.filter
def histogram(answer_list, args='format=html'):
    """ Generate Postscript code for a histogram of the provided results, save it and return a string pointing to it. """
    from django.conf import settings
    HISTOGRAM_PATH = 'images/histograms/'
    HISTOGRAM_DIR = settings.MEDIA_ROOT + HISTOGRAM_PATH
    import tempfile

    image_width = 2.75

    args_dict = QueryDict(args)

    processed_list = []
    for ans in answer_list:
        if isinstance(ans, list):
            processed_list.extend(ans)
        else:
            processed_list.append(ans)
    answer_list = processed_list

    #   Place results in key, value pairs where keys contain values and values contain frequencies.
    context = {}
    context['title'] = 'Results of survey'
    context['num_responses'] = len(answer_list)

    if args_dict.get('max'):
        context['results'] = [{'value': str(x), 'freq': 0} for x in range(1, int(args_dict.get('max')) + 1)]
    elif args_dict.get('opts'):
        context['results'] = [{'value': str(x), 'freq': 0} for x in args_dict.get('opts').split("|")]
    else:
        context['results'] = []
    max_answer_length = 0
    for ans in answer_list:
        try:
            i = [r['value'] for r in context['results']].index(str(ans))
            context['results'][i]['freq'] += 1
        except ValueError:
            context['results'].append({'value': ans, 'freq': 1})
        if len(ans) > max_answer_length:
            max_answer_length = len(ans)

    context['results'].sort(key=lambda x: x['value'])

    #   Compute simple stats so postscript doesn't have to
    max_freq = 0
    context['num_keys'] = len(context['results'])
    for item in context['results']:
        if item['freq'] > max_freq:
            max_freq = item['freq']
            context['max_freq'] = max_freq

    #   Might we have trouble making text not overlap? 36 is an arbitrary limit.
    if context['num_keys'] * max_answer_length > 36:
        context['crowded'] = True
    else:
        context['crowded'] = False

    import hashlib
    file_base = hashlib.sha1(pickle.dumps(context)).hexdigest()
    file_name = os.path.join(tempfile.gettempdir(), file_base+'.eps')
    template_file = os.path.join(settings.TEMPLATES[0]['DIRS'][0],
                                 'survey', 'histogram_base.eps')

    context['file_name'] = file_name # This guy depends on the SHA-1

    #  No point in SHA-1 caching these guys; they're in /tmp
    file_contents = loader.render_to_string(template_file, context)
    file_obj = open(file_name, 'w')
    file_obj.write(file_contents)
    file_obj.close()

    #   We have the necessary EPS file, now we do any necessary conversions and include
    #   it into the output.
    png_filename = "%s.png" % file_base
    if args_dict.get('format') == 'tex':
        image_path = os.path.join(tempfile.gettempdir(), png_filename)
    elif args_dict.get('format') == 'html':
        image_path = os.path.join(HISTOGRAM_DIR, png_filename)
    if not os.path.exists(image_path):
        subprocess.call(['gs', '-dBATCH', '-dNOPAUSE', '-dTextAlphaBits=4',
                         '-dDEVICEWIDTHPOINTS=216', '-dDEVICEHEIGHTPOINTS=162',
                         '-sDEVICE=png16m', '-R96',
                         '-sOutputFile=' + image_path, file_name])
    if args_dict.get('format') == 'tex':
        return '\includegraphics[width=%fin]{%s}' % (image_width, image_path)
    if args_dict.get('format') == 'html':
        return '<img src="%s" />' % ('/media/' + HISTOGRAM_PATH + png_filename)

@register.filter
def answer_to_list(ans):
    # If the answer is not a list, turn it into a one-element list.
    # Then if the answer is a list of classes, return a list of their titles.
    if isinstance(ans.answer, list):
        value = ans.answer
    else:
        value = [ ans.answer ]

    if ans.question.question_type.name == 'Favorite Class':
        return [ c.emailcode() + ': ' + c.title for c in ClassSubject.objects.filter(id__in=value) ]

    return value

@register.filter
def favorite_classes(answer_list, limit=20):
    result_list = []
    class_dict = {}

    for a in answer_list:
        if isinstance(a, list):
            l = a
        else:
            l = [ a ]
        for i in l:
            ind = int(i)
            if ind in class_dict:
                class_dict[ind] += 1
            else:
                class_dict[ind] = 1

    key_list = class_dict.keys()
    key_list.sort(key=lambda x: -class_dict[x])

    max_count = min(limit, len(key_list))

    for key in key_list[:max_count]:
        cl = ClassSubject.objects.filter(id=key)
        if cl.count() == 1:
            result_list.append({'title': '%s: %s' % (cl[0].emailcode(), cl[0].title), 'votes': class_dict[key]})

    return result_list

@register.filter(is_safe=True)
def dictlookup(key,dict):
    '''Get the correct column for the answer, for dump_survey.'''
    return dict[key]
