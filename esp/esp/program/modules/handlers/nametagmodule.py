
from __future__ import absolute_import
from __future__ import division
from six.moves import range
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
import base64
from io import BytesIO
from itertools import groupby
import json
import os.path
import re
import subprocess

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.template import loader
from reversion import revisions as reversion
from PIL import Image
from six.moves.urllib.parse import urlparse

from esp.middleware import ESPError
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.modules.handlers.listgenmodule import ListGenModule
from esp.program.models import NametagBack, RegistrationProfile
from esp.users.controllers.usersearch import UserSearchController
from esp.tagdict.models import Tag
from esp.users.models import ESPUser
from esp.utils.latex import gen_latex, render_to_latex, texsafe
from esp.utils.web import render_to_response

from django.contrib.auth.models import Group
from django.db.models.query import Q


# Sheet geometry, in inches.  The grid of cards is centered on the page.
PAGE_WIDTH = 8.5
PAGE_HEIGHT = 11.0
CARD_WIDTH = 3.9
CARD_HEIGHT = 3.0
COLUMNS = 2
ROWS = 3
CARDS_PER_PAGE = COLUMNS * ROWS
GRID_LEFT = (PAGE_WIDTH - COLUMNS * CARD_WIDTH) / 2
GRID_TOP = (PAGE_HEIGHT - ROWS * CARD_HEIGHT) / 2
FRONT_MARGIN = 0.1
BACK_MARGIN = 0.15
MIN_BACK_MARGIN = 0.1
MARGIN_TOLERANCE = 0.005
INK_THRESHOLD = 240
TEST_LABEL_INSET = 0.05

MAX_PRINTER_OFFSET = 1.0
MAX_BACK_SOURCE_LENGTH = 50000
BACK_COMPILE_TIMEOUT = 8
MAX_FLAGGED_NAMES = 12

# The scales on the back test sheet span +/- 0.5in with marks every 0.025in.
SCALE_MINOR_STEP = 0.025
SCALE_STEPS = 20
SCALE_STEPS_PER_MAJOR = 4
SCALE_MAJOR_LENGTH = 0.16
SCALE_MINOR_LENGTH = 0.08
SCALE_INSET = 0.1
SCALE_REFERENCE_LENGTH = 0.5
CUT_MARK_LENGTH = 0.85
CALIBRATION_MARK_LENGTH = 0.2
LOGO_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.pdf')


def _tex(value):
    return texsafe(value if value is not None else '')[0]


def _place(x, y, content):
    """ LaTeX to draw content with its top left corner at (x, y). """
    return r'\put(%.3f,%.3f){\makebox(0,0)[lt]{%s}}' % (x, y, content)


def _card_corner(slot, x_offset=0.0, y_offset=0.0):
    """ Top left corner of a card; x_offset moves right and y_offset moves down. """
    return (GRID_LEFT + (slot % COLUMNS) * CARD_WIDTH + x_offset,
            PAGE_HEIGHT - GRID_TOP - (slot // COLUMNS) * CARD_HEIGHT - y_offset)


def _cut_marks(length=CUT_MARK_LENGTH):
    """ Lines below the grid showing where to cut the columns. """
    return [r'\put(%.3f,%.3f){\line(0,1){%.3f}}' % (GRID_LEFT + column * CARD_WIDTH, GRID_TOP - length, length)
            for column in range(COLUMNS + 1)]


def _grid_lines(x_offset=0.0, y_offset=0.0):
    """ The outline of every card, drawing each shared edge only once. """
    left, top = _card_corner(0, x_offset, y_offset)
    width = COLUMNS * CARD_WIDTH
    height = ROWS * CARD_HEIGHT
    lines = [r'\put(%.3f,%.3f){\line(0,1){%.3f}}' % (left + column * CARD_WIDTH, top - height, height)
             for column in range(COLUMNS + 1)]
    lines.extend(r'\put(%.3f,%.3f){\line(1,0){%.3f}}' % (left, top - row * CARD_HEIGHT, width)
                 for row in range(ROWS + 1))
    return lines


def _front_reference_marks():
    """ Lines on the front calibration sheet to read against the scales on its back.

    The grid's center line is the reference for the top and bottom scales.
    """
    center_y = PAGE_HEIGHT / 2
    grid_right = PAGE_WIDTH - GRID_LEFT
    return [r'\put(%.3f,%.3f){\line(0,1){%.3f}}' % (PAGE_WIDTH / 2, PAGE_HEIGHT - GRID_TOP, CALIBRATION_MARK_LENGTH),
            r'\put(%.3f,%.3f){\line(1,0){%.3f}}' % (GRID_LEFT, center_y, SCALE_REFERENCE_LENGTH),
            r'\put(%.3f,%.3f){\line(1,0){%.3f}}' % (grid_right - SCALE_REFERENCE_LENGTH, center_y, SCALE_REFERENCE_LENGTH)]


def _offset_scale(x, y, horizontal, direction):
    """ A ruler whose zero is at (x, y), with ticks extending toward direction.

    Horizontal scales read positive to the right and vertical scales read
    positive downward, matching the printer offset fields.
    """
    items = []
    for step in range(-SCALE_STEPS, SCALE_STEPS + 1):
        distance = step * SCALE_MINOR_STEP
        major = step % SCALE_STEPS_PER_MAJOR == 0
        length = SCALE_MAJOR_LENGTH if major else SCALE_MINOR_LENGTH
        reach = direction * (SCALE_MAJOR_LENGTH + 0.03)
        label = '0' if step == 0 else '%.1f' % distance
        if horizontal:
            items.append(r'\put(%.3f,%.3f){\line(0,%d){%.3f}}' % (x + distance, y, direction, length))
            if major:
                items.append(r'\put(%.3f,%.3f){\makebox(0,0)[%s]{\rotatebox{90}{\ntscale{%s}}}}'
                             % (x + distance, y + reach, 'b' if direction > 0 else 't', label))
        else:
            items.append(r'\put(%.3f,%.3f){\line(%d,0){%.3f}}' % (x, y - distance, direction, length))
            if major:
                items.append(r'\put(%.3f,%.3f){\makebox(0,0)[%s]{\ntscale{%s}}}'
                             % (x + reach, y - distance, 'l' if direction > 0 else 'r', label))
    return items


def _offset_scales(x_offset, y_offset):
    """ The four scales for the back calibration sheet, inside the cards.
    They move with the offsets, so a corrected sheet reads zero. """
    center_x = PAGE_WIDTH / 2 + x_offset
    center_y = PAGE_HEIGHT / 2 - y_offset
    grid_left = GRID_LEFT + x_offset
    grid_right = PAGE_WIDTH - GRID_LEFT + x_offset
    return (_offset_scale(center_x, PAGE_HEIGHT - GRID_TOP - SCALE_INSET - y_offset, True, -1)
            + _offset_scale(center_x, GRID_TOP + SCALE_INSET - y_offset, True, 1)
            + _offset_scale(grid_left, center_y, False, 1)
            + _offset_scale(grid_right, center_y, False, -1))


def _centered_labels(labels, x_offset=0.0, y_offset=0.0):
    """ Text centered in each card. """
    items = []
    for slot, label in enumerate(labels):
        x, y = _card_corner(slot, x_offset, y_offset)
        items.append(r'\put(%.3f,%.3f){\makebox(%.3f,%.3f)[c]{\ntcenterlabel{%s}}}'
                     % (x, y - CARD_HEIGHT, CARD_WIDTH, CARD_HEIGHT, label))
    return items


def calibration_pages(x_offset, y_offset):
    """ A two-sided sheet for measuring how far a printer shifts the backs. """
    front = _grid_lines() + _cut_marks(CALIBRATION_MARK_LENGTH) + _front_reference_marks()
    front += _centered_labels([r'\#%d' % (slot + 1) for slot in range(CARDS_PER_PAGE)])
    back = _grid_lines(x_offset, y_offset) + _offset_scales(x_offset, y_offset)
    back += _centered_labels([r'\#%d back' % ((slot ^ 1) + 1) for slot in range(CARDS_PER_PAGE)], x_offset, y_offset)
    back.append(_place(GRID_LEFT, PAGE_HEIGHT - 0.35, r'\ntscalehelp'))
    return [front, back]


def numbered_page():
    """ The sheet showing where each nametag on a page goes. """
    page = _grid_lines()
    for slot in range(CARDS_PER_PAGE):
        x, y = _card_corner(slot)
        page.append(_place(x + TEST_LABEL_INSET, y - TEST_LABEL_INSET, r'\ntlabel{\#%d}' % (slot + 1)))
    return page


def _logo_tex():
    """ LaTeX for the nametag logo, or nothing if pdflatex can't safely use it. """
    url = Tag.getTag('nametag_logo_url')
    if not url:
        return ''
    url_path = urlparse(url).path
    if not url_path.startswith(settings.MEDIA_URL):
        return ''
    relative_path = url_path[len(settings.MEDIA_URL):]
    full_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, relative_path))
    if (not re.match(r'^[\w./-]+$', full_path)
            or not full_path.startswith(os.path.normpath(settings.MEDIA_ROOT) + os.sep)
            or os.path.splitext(full_path)[1].lower() not in LOGO_EXTENSIONS
            or not os.path.isfile(full_path)):
        return ''
    return r'\includegraphics[height=0.35in]{%s}' % full_path


def _front_tex(user, program_name, logo, site_line):
    lines = [r'\ntprogram{%s}' % _tex(program_name), r'\ntname{%s}' % _tex(user.get('name'))]
    if user.get('pronoun'):
        lines.append(r'\ntpronoun{(%s)}' % _tex(user['pronoun']))
    lines.append(r'\nttitle{%s}' % _tex(user.get('title')))
    id_line = ''
    if user.get('id'):
        id_line = r'\ntid{%s (ID: %s)}' % (_tex(user.get('username', '')), _tex(user['id']))
    return r'\ntfront{%s}{\ntfooter{%s}{%s}{%s}}' % (''.join(lines), logo, id_line, site_line)


def _barcode_back_tex(user):
    if not user.get('id'):
        return ''
    checkin = ''
    if user.get('hash'):
        checkin = r'\ntcheckin{%s}' % _tex(user['hash'])
    return r'\ntbarcodeback{%s}{%d}' % (checkin, int(user['id']))


def _back_context(source):
    return {'MEDIA_ROOT': settings.MEDIA_ROOT, 'paper_width': CARD_WIDTH, 'paper_height': CARD_HEIGHT,
            'back_source': source, 'back_content_width': CARD_WIDTH - 2 * BACK_MARGIN,
            'back_corner_x': BACK_MARGIN, 'back_corner_y': CARD_HEIGHT - BACK_MARGIN}


def render_back_preview_tex(source):
    return loader.get_template('program/modules/nametagmodule/back_preview.tex').render(_back_context(source))


def check_nametag_back(source):
    """ Compile a back on its own.  Returns a dict with any 'error' and 'warnings'. """
    tex = render_back_preview_tex(source)
    try:
        log = gen_latex(tex, 'log', timeout=BACK_COMPILE_TIMEOUT, cleanup=True)
    except subprocess.TimeoutExpired:
        return {'error': 'LaTeX took too long and was stopped. Check for a macro that never finishes.'}

    log_lines = log.splitlines()
    marker = tex.split('\n').index('%NAMETAG_BACK_START') + 1
    error = next((line[2:].strip() for line in log_lines if line.startswith('! ')), None)
    if error:
        for line in log_lines:
            match = re.match(r'l\.(\d+)', line)
            if match and int(match.group(1)) > marker:
                error = 'Line %d: %s' % (int(match.group(1)) - marker, error)
                break
        return {'error': error}
    if 'NAMETAG_BACK_COMPLETE' not in log:
        return {'error': 'The back ended early. Check for a stray \\end{document}.'}
    return {'error': None}


def _margin_warning(png):
    '''Why a rendered back is too close to the card's edge, or None if it's fine.

    This looks at the rendered image rather than LaTeX's box sizes, which
    negative spacing and the like can hide things from.
    '''
    image = Image.open(BytesIO(png)).convert('RGBA')
    canvas = Image.new('RGBA', image.size, 'white')
    canvas.alpha_composite(image)
    ink = canvas.convert('L').point(lambda value: 255 if value < INK_THRESHOLD else 0).getbbox()
    if ink is None:
        return None
    width, height = image.size
    per_inch_x = float(width) / CARD_WIDTH
    per_inch_y = float(height) / CARD_HEIGHT
    margins = [('left', ink[0] / per_inch_x), ('right', (width - ink[2]) / per_inch_x),
               ('top', ink[1] / per_inch_y), ('bottom', (height - ink[3]) / per_inch_y)]
    tight = ['%s (%.2fin)' % margin for margin in margins if margin[1] < MIN_BACK_MARGIN - MARGIN_TOLERANCE]
    if not tight:
        return None
    return 'WARNING: too close to the edge of the card: %s. Keep at least %.1fin on every side, or sloppy cutting may clip it.' % (', '.join(tight), MIN_BACK_MARGIN)


def nametag_back_groups(program):
    """ All saved backs grouped for a dropdown, newest programs first.

    The current program is always included, since it offers "Create new".
    """
    backs_by_program = {program.id: (program, [])}
    backs = NametagBack.objects.select_related('program').order_by('name')
    for back in backs:
        backs_by_program.setdefault(back.program_id, (back.program, []))[1].append(back)
    groups = []
    for program_id in sorted(backs_by_program, reverse=True):
        group_program, group_backs = backs_by_program[program_id]
        groups.append({'label': group_program.niceName(), 'backs': group_backs, 'is_current': program_id == program.id})
    return groups


def _back_preview(source):
    """ Compile and render a back.  Returns a dict with any 'error' or
    'warning', and an 'image'. """
    result = check_nametag_back(source)
    result.update({'image': None, 'warning': None})
    if not result['error']:
        try:
            png = gen_latex(render_back_preview_tex(source), 'png', timeout=BACK_COMPILE_TIMEOUT, cleanup=True)
        except (ESPError, subprocess.TimeoutExpired):
            result['error'] = 'The back compiled, but its preview image could not be made.'
        else:
            result['image'] = 'data:image/png;base64,' + base64.b64encode(png).decode('ascii')
            result['warning'] = _margin_warning(png)
    return result


def _json_response(data):
    return HttpResponse(json.dumps(data), content_type='application/json')


class NameTagModule(ProgramModuleObj):
    doc = """This module allows you to generate a bunch of IDs for users that match specific criteria."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Nametag Generation",
            "link_title": "Generate Nametags",
            "module_type": "manage",
            "seq": 100,
            "choosable": 1,
            }

    @main_call
    @needs_admin
    def selectidoptions(self, request, tl, one, two, module, extra, prog):
        """ Display a page for admins to pick users for nametags """
        context = {'module': self}
        context['groups'] = Group.objects.all()
        usc = UserSearchController()
        context.update(usc.prepare_context(prog, target_path='/manage/%s/generatetags' % prog.url))
        context['combo_form'] = False
        context['include_continue'] = False
        context['self_checkin'] = Tag.getProgramTag('student_self_checkin', program = prog) == 'code'
        context['back_groups'] = nametag_back_groups(prog)

        return render_to_response(self.baseDir()+'selectoptions.html', request, context)

    def nametag_data(self, users_list1, user_title1, users_list2 = ESPUser.objects.none(), user_title2 = None, program = None):
        users = []
        users_list = [ user for user in users_list1 | users_list2]
        users_list = sorted([x for x in users_list if len(x.first_name+x.last_name)])

        for user in users_list:
            prof = RegistrationProfile.getLastProfile(user)
            if user in users_list1:
                title = user_title1
            else:
                title = user_title2
            if prof.teacher_info is not None:
                pronoun = prof.teacher_info.pronoun
            elif prof.student_info is not None:
                pronoun = prof.student_info.pronoun
            else:
                pronoun = None
            user_dict = {'title': title,
                         'name' : '%s %s' % (user.first_name, user.last_name),
                         'id'   : user.id,
                         'username': user.username,
                         'pronoun': pronoun}
            if program and Tag.getProgramTag('student_self_checkin', program = program) == 'code':
                user_dict['hash'] = user.userHash(program)
            users.append(user_dict)
        return users

    @aux_call
    @needs_admin
    def generatetags(self, request, tl, one, two, module, extra, prog):
        """ generate nametags """

        # Default to students
        if 'type' not in request.POST:
            raise ESPError("You need to select the TYPE of Name Tag to print. (students,teachers,etc)", log=False)
        idtype = request.POST['type']

        x_offset = self._printer_offset(request, 'back_x_offset')
        y_offset = self._printer_offset(request, 'back_y_offset')
        file_type = extra if extra in ('tex', 'log') else 'pdf'
        if idtype == 'calibration':
            context = _back_context('')
            context.update({'paper_width': PAGE_WIDTH, 'paper_height': PAGE_HEIGHT, 'has_back': False,
                            'pages': calibration_pages(x_offset, y_offset)})
            return render_to_latex(self.baseDir()+'ids.tex', context, file_type)

        users = []

        user_title = idtype

        if idtype == 'aul':
            user_title = request.POST['blanktitle']
            data = ListGenModule.processPost(request)
            usc = UserSearchController()
            filterObj = usc.filter_from_postdata(prog, data)
            users = self.nametag_data(ESPUser.objects.filter(filterObj.get_Q()).distinct(), user_title, program = prog)

        elif idtype == 'students':
            user_title = "Student"
            student_dict = self.program.students(QObjects = True)
            if 'classreg' in student_dict:
                students = ESPUser.objects.filter(student_dict['classreg']).distinct()
            else:
                students = ESPUser.objects.filter(student_dict['confirmed']).distinct()

            users = self.nametag_data(students, user_title, program = prog)

        elif idtype == 'teacher':
            user_title = "Teacher"
            teachers = self.program.teachers()['class_approved'].distinct()

            users = self.nametag_data(teachers, user_title)

        elif idtype == 'teachermoderators':
            user_title = "Teacher"
            user_title2 = self.program.getModeratorTitle()
            teacher_dict = self.program.teachers()
            teachers = teacher_dict['class_approved'].distinct()
            moderators = teacher_dict['assigned_moderator'].distinct()

            users = self.nametag_data(teachers, user_title, moderators, user_title2)

        elif idtype == 'moderators':
            user_title = self.program.getModeratorTitle()
            teacher_dict = self.program.teachers()
            moderators = teacher_dict['assigned_moderator'].distinct()

            users = self.nametag_data(moderators, user_title)

        elif idtype == 'other':
            user_title = request.POST['blanktitle']
            if request.POST['group'] == '':
                raise ESPError("You need to select a group", log=False)
            group = request.POST['group']
            user_Q = Q(groups=group)
            users_list = ESPUser.objects.filter(user_Q).distinct()

            users = self.nametag_data(users_list, user_title)

        elif idtype == 'volunteers':
            user_title = "Volunteer"
            volunteer_dict = self.program.volunteers(QObjects=True)
            volunteers = ESPUser.objects.filter(volunteer_dict['volunteer_all']).distinct()

            users = self.nametag_data(volunteers, user_title)

        elif idtype == 'misc':
            users = []
            misc = request.POST['misc_info']
            for user in misc.split("\n"):
                arruser = user.split(",", 2)

                if len(arruser) >= 2:
                    user_title = arruser[1].strip()
                    pronoun = arruser[2].strip() if len(arruser) >= 3 else None
                    users.append({'title': user_title,
                                  'name' : arruser[0].strip(),
                                  'id'   : '',
                                  'pronoun': pronoun})


        elif idtype == 'blank':
            users = []
            user_title = request.POST['blanktitle']
            for i in range(int(request.POST['number'])):
                users.append({'title': user_title,
                              'name' : '',
                              'id'   : ''})

        numperpage = CARDS_PER_PAGE


        expanded = [[] for i in range(numperpage)]

        for i in range(len(users)):
            expanded[(i*numperpage)//len(users)].append(users[i])

        users = []

        for i in range(len(expanded[0])):
            for j in range(len(expanded)):
                if len(expanded[j]) <= i:
                    users.append({'title': user_title,
                                  'name' : '',
                                  'id'   : ''})
                else:
                    users.append(expanded[j][i])

        barcodes = 'barcodes' in request.POST
        back = self._selected_back(request, prog)
        if back and barcodes:
            raise ESPError("A nametag back and barcodes both print on the back of the card. Please choose one.", log=False)
        if back:
            problem = check_nametag_back(back.source)['error']
            if problem:
                raise ESPError('The back "%s" needs fixing before it can be printed. %s' % (back.name, problem), log=False)

        group_name = Tag.getTag('full_group_name') or '%s %s' % (settings.INSTITUTION_NAME, settings.ORGANIZATION_SHORT_NAME)
        phone_number = Tag.getTag('group_phone_number')
        site_line = _tex('http://%s' % request.META.get('HTTP_HOST', ''))
        if phone_number:
            site_line += ' ' + _tex(phone_number)
        logo = _logo_tex()
        program_name = request.POST['progname']

        has_backs = barcodes or back is not None
        pages = [numbered_page()]
        if has_backs:
            # An empty side, so that later fronts and backs stay paired up.
            pages.append([])

        flagged = []
        for start in range(0, len(users), CARDS_PER_PAGE):
            sheet = users[start:start + CARDS_PER_PAGE]
            front_page = _cut_marks()
            back_page = _cut_marks()
            for slot, user in enumerate(sheet):
                printed_name, altered = texsafe(user.get('name') or '')
                if altered:
                    flagged.append('%s%s' % (printed_name, ' (ID %s)' % user['id'] if user.get('id') else ''))
                x, y = _card_corner(slot)
                front_page.append(_place(x + FRONT_MARGIN, y - FRONT_MARGIN, _front_tex(user, program_name, logo, site_line)))

                # The sheet flips over its long edge, so the card behind this
                # one is in the other column.
                x, y = _card_corner(slot ^ 1, x_offset, y_offset)
                if back:
                    back_page.append(_place(x + BACK_MARGIN, y - BACK_MARGIN, r'\usebox{\backbox}'))
                elif barcodes:
                    back_page.append(_place(x, y, _barcode_back_tex(user)))
            pages.append(front_page)
            if has_backs:
                pages.append(back_page)

        if flagged:
            note = r'\parbox[t]{7.8in}{\small\bfseries %d name(s) had characters that could not be printed; check these nametags: %s%s}' % (
                len(flagged), _tex('; '.join(flagged[:MAX_FLAGGED_NAMES])), ' ...' if len(flagged) > MAX_FLAGGED_NAMES else '')
            pages[0].append(_place(GRID_LEFT, PAGE_HEIGHT - 0.15, note))

        context = _back_context(back.source if back else '')
        context.update({'paper_width': PAGE_WIDTH, 'paper_height': PAGE_HEIGHT, 'has_back': back is not None,
                        'barcodes': barcodes, 'pages': pages, 'group_name': group_name})
        return render_to_latex(self.baseDir()+'ids.tex', context, file_type)

    def _selected_back(self, request, prog):
        back_id = request.POST.get('nametag_back')
        if not back_id:
            return None
        back = self._posted_back(back_id, prog)
        if not back:
            raise ESPError("Please save this back to %s before printing it." % prog.niceName(), log=False)
        return back

    def _printer_offset(self, request, field):
        try:
            offset = float(request.POST.get(field) or 0)
        except ValueError:
            offset = None
        if offset is None or not -MAX_PRINTER_OFFSET <= offset <= MAX_PRINTER_OFFSET:
            raise ESPError("Printer alignment offsets must be numbers of inches between -%s and %s." % (MAX_PRINTER_OFFSET, MAX_PRINTER_OFFSET), log=False)
        return offset

    def _posted_back(self, value, prog=None):
        """ The back with this id, optionally only if it belongs to prog. """
        if not value.isdigit():
            return None
        backs = NametagBack.objects.select_related('program').filter(id=value)
        if prog:
            backs = backs.filter(program=prog)
        return backs.first()

    @aux_call
    @needs_admin
    def nametagbackload(self, request, tl, one, two, module, extra, prog):
        """ A back's source and preview for the editor. """
        back = self._posted_back(request.GET.get('back', ''))
        if not back:
            return _json_response({'error': 'That nametag back no longer exists.'})
        result = _back_preview(back.source)
        result.update({'id': back.id, 'name': back.name, 'source': back.source, 'importing': back.program_id != prog.id})
        return _json_response(result)

    @aux_call
    @needs_admin
    def nametagbacksave(self, request, tl, one, two, module, extra, prog):
        """ Save the editor's contents to this program and preview the result. """
        if request.method != 'POST':
            return _json_response({'error': 'Backs can only be saved with a POST.'})
        source = request.POST.get('source', '')
        name = request.POST.get('name', '').strip()
        error = self._back_save_error(name, source)
        if error:
            return _json_response({'error': error, 'image': None})
        result = _back_preview(source)
        if result['error']:
            return _json_response(result)
        saved, error = self._save_back(prog, request.user, self._posted_back(request.POST.get('back_id', ''), prog), name, source)
        if error:
            return _json_response({'error': error, 'image': None})
        return self._saved_response(prog, saved, result)

    @aux_call
    @needs_admin
    def nametagbackimport(self, request, tl, one, two, module, extra, prog):
        """ Copy another program's back into this one.  This works even if the
        back has problems, since importing it is the only way to fix them. """
        if request.method != 'POST':
            return _json_response({'error': 'Backs can only be imported with a POST.'})
        original = self._posted_back(request.POST.get('back_id', ''))
        if not original or original.program_id == prog.id:
            return _json_response({'error': 'That back can no longer be imported.', 'image': None})
        name = request.POST.get('name', '').strip()
        error = self._back_save_error(name, original.source)
        if error:
            return _json_response({'error': error, 'image': None})
        saved, error = self._save_back(prog, request.user, None, name, original.source,
                                       'Imported from %s: %s' % (original.program.niceName(), original.name))
        if error:
            return _json_response({'error': error, 'image': None})
        return self._saved_response(prog, saved, _back_preview(saved.source))

    def _saved_response(self, prog, saved, result):
        options = loader.render_to_string(self.baseDir()+'back_options.html', {'back_groups': nametag_back_groups(prog)})
        result.update({'id': saved.id, 'name': saved.name, 'options_html': options})
        return _json_response(result)

    def _back_save_error(self, name, source):
        if not name:
            return 'Please give this back a name.'
        if len(name) > NametagBack._meta.get_field('name').max_length:
            return 'That name is too long.'
        if not source.strip():
            return 'A saved back needs some content. Choose "Blank" when printing if you want no back.'
        if len(source) > MAX_BACK_SOURCE_LENGTH:
            return 'That back is too long.'
        return None

    def _save_back(self, prog, user, loaded, name, source, comment=None):
        """ Update the loaded back of this program, or create a new back,
        recording who did it in the back's reversion history. """
        clashes = NametagBack.objects.filter(program=prog, name=name)
        if loaded:
            clashes = clashes.exclude(id=loaded.id)
        if clashes.exists():
            return None, '%s already has a back named "%s". Please pick another name.' % (prog.niceName(), name)
        if comment is None:
            if not loaded:
                comment = 'Created'
            elif loaded.name != name:
                comment = 'Renamed from "%s"' % loaded.name
            else:
                comment = 'Edited'
        back = loaded or NametagBack(program=prog)
        back.name = name
        back.source = source
        with transaction.atomic(), reversion.create_revision():
            back.save()
            reversion.set_user(user)
            reversion.set_comment(comment)
        return back, None

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
