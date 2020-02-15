
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
from esp.users.models import ContactInfo, ESPUser
from esp.program.models import ArchiveClass, ClassSubject, ClassCategories
from esp.utils.web import render_to_response
from django.db.models.query import QuerySet
from django.http import HttpResponse, Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from datetime import datetime

#    Two inputs to each function:
#    -    category: what you sort or view by
#        (such as: year, program, subject category, title)
#    -    options: the particular filter for that data
#        (eg. 2004, Splash, ComputerScience)

class ArchiveFilter(object):
    category = ""
    options = ""
    def __init__(self, category = "", options = ""):
        self.category = unicode(category)
        self.options  = unicode(options)

    def __unicode__(self):
        return '%s, %s' % (self.category, self.options)

def compute_range(postvars, num_records):
    default_num_records = 10
    results_start = 0
    results_end = None
    if 'results_start' in postvars:
        results_start = int(postvars['results_start'])
    if 'results_end' in postvars:
        results_end = int(postvars['results_end'])
    if (num_records > default_num_records) and results_end == None:
        if postvars.get('max_num_results') == "Show all":
            results_end = num_records
        elif postvars.get('max_num_results'):
            results_end = results_start + int(postvars['max_num_results'])
        else:
            results_end = results_start + default_num_records

    return {'start': results_start, 'end': results_end}

def extract_criteria(postvars):
    #    Use filters
    criteria = []
    for key in postvars.keys():
        if len(postvars[key]) > 0 and key.find("filter_") != -1 and len(key) > 7: criteria.append(ArchiveFilter(category = key[7:], options = postvars[key]))

    return criteria

def filter_archive(records, criteria):
    result = records
    for c in criteria:
        if c.category == 'year':
            result = result.filter(year = c.options)
        elif c.category == 'program':
            result = result.filter(program__iexact = c.options)
        elif c.category == 'title':
            result = result.filter(title__istartswith = c.options)
        elif c.category == 'category':
            result = result.filter(category__istartswith = c.options)
        elif c.category == 'teacher':
            result = result.filter(teacher__icontains = c.options)
        elif c.category == 'description':
            result = result.filter(description__icontains = c.options)

    return result

def title_heading(title_content):
    if len(title_content) > 0:
        return title_content[0]
    else:
        return '[No Title]'

def archive_classes(request, category, options, sortorder = None):
    context = {'selection': 'Classes'}
    context['category'] = category
    context['options'] = options

    #    Take filtering criteria both from form and from URL
    if category != None and options != None:
        url_criterion = ArchiveFilter(category = category, options = options)
        criteria_list = [url_criterion]
    else:
        criteria_list = []

    criteria_list += extract_criteria(request.POST)
    criteria_list += extract_criteria(request.GET)

    category_list = list(ArchiveClass.objects.all().values_list('category', flat=True).distinct())
    program_list = list(ArchiveClass.objects.all().values_list('program', flat=True).distinct())

    category_dict = {}
    classcatList = ClassCategories.objects.all()
    for letter in map(chr, range(65, 91)):
        category_dict[letter] = 'Unknown Category'

    for category in classcatList:
        category_dict[category.category[0].upper()] = category.category

    filter_keys = {'category': [{'name': c, 'value': c, 'selected': False} for c in category_list],
            'year': [{'name': str(y), 'value': str(y), 'selected': False} for y in range(1998, datetime.now().year + 1)],
            'title': [{'name': 'Starts with ' + letter, 'value': letter, 'selected': False} for letter in map(chr, range(65,91))],
             'program': [{'name': p, 'value': p, 'selected': False} for p in program_list],
            'teacher': [{}],
            'description': [{}]
            }
    if 'filter_teacher' in request.POST: filter_keys['teacher'][0]['default_value'] = request.POST['filter_teacher']
    if 'filter_description' in request.POST: filter_keys['description'][0]['default_value'] = request.POST['filter_description']

    results = filter_archive(ArchiveClass.objects.all(), criteria_list)

    #    Sort the results by the specified order
    if (not isinstance(sortorder, list)) or len(sortorder) < 1:
        sortorder = ['year', 'category', 'program', 'title', 'teacher', 'description']

    sortorder.reverse()
    for parameter in sortorder:
        results = results.order_by(parameter)
    sortorder.reverse()

    context['sortorder'] = sortorder

    for c in criteria_list:
        for k in filter_keys[c.category]:
            if 'name' in k and 'value' in k:
                if c.options == k['value']:
                    k['selected'] = True

    context['sortparams'] = [{'name': k, 'options': filter_keys[k]} for k in filter_keys.keys()]

    #    Display the appropriate range of results
    postvars = request.POST.copy()
    relevant_keys = ['max_num_results', 'results_start', 'results_end']
    for k in relevant_keys:
        if k in request.GET:
            postvars[k] = request.GET[k]

    res_range = compute_range(postvars, results.count())
    context['results_range'] = res_range

    #    Deal with the Django bug preventing you from using no "end"
    if res_range['end'] is None:
        res_range['end'] = results.count()

    #    Rename all of the class categories and uppercase the programs
    for entry in results[res_range['start']:res_range['end']]:
        entry.category = category_dict[entry.category[:1].upper()]
        entry.program = entry.program.upper()
        #    entry.title = entry.title.capitalize()

    #    Compute the headings for the 'jump to category' part
    if sortorder[0] == 'title':
        headings = [title_heading(item.__dict__['title']) for item in results[res_range['start']:res_range['end']]]
    else:
        headings = [item.__dict__[sortorder[0]] for item in results[res_range['start']:res_range['end']]]

    context['headings'] = list(set([unicode(h) for h in headings]))
    context['headings'].sort()

    #    Fill in context some more
    context['num_results'] = results.count()
    context['results'] = list(results[res_range['start']:res_range['end']])
    context['results_range']['start'] = context['results_range']['start'] + 1
    if res_range['end'] > context['num_results']:
        context['results_range']['end'] = context['num_results']
    if 'max_num_results' in request.POST:
        context['max_num_results'] = request.POST['max_num_results']
    else:
        context['max_num_results'] = '25'
    context['num_results_list'] = ['10', '25', '50', '100', '250', 'Show all']
    context['num_results_shown'] = len(context['results'])

    return render_to_response('program/archives.html', request, context)

def archive_teachers(request, category, options):
    context = {'selection': 'Teachers'}
    context['category'] = category
    context['options'] = options

    return render_to_response('program/archives.html', request, context)

def archive_programs(request, category, options):
    context = {'selection': 'Programs'}
    context['category'] = category
    context['options'] = options

    return render_to_response('program/archives.html', request, context)

archive_handlers = {    'classes': archive_classes,
            'teachers': archive_teachers,
            'programs': archive_programs,
        }

