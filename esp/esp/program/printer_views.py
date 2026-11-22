"""The Printers page (/manage/printers/), for every program: which printer
prints for each day-of location (a laptop running the printing page, or a
network printer the server prints to), and the print queue. Locations and the
queue aren't per program (esp.program.controllers.printing), so neither is
this page; each program's onsite page links here (OnsitePrintSchedules, whose
old /onsite/<program>/printers_* URLs still lead to these views, for laptops
left printing from them). Used by admins and anyone with onsite access to some
program (day-of volunteers set up laptop printing)."""
from __future__ import absolute_import
from __future__ import unicode_literals

import functools
import json

from six.moves.urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils import timezone

from esp.middleware.esperrormiddleware import ESPError_NoLog
from esp.program.controllers import dayof, printing
from esp.utils import print_server
from esp.utils.models import Printer, PrintRequest
from esp.utils.web import render_to_response

BASE_URL = '/manage/printers/'
TEMPLATES = 'program/modules/onsiteprintschedules/'
#   The program whose onsite page linked here (for the page's "return" link)
SESSION_PROGRAM = 'printers_program'


def can_use_printers(user):
    """ Admins, and anyone with onsite (or admin) access to any program. """
    from esp.users.models import Permission
    if not user.is_authenticated or user.id is None:
        return False
    if getattr(user, 'onsite_local', False) is True or user.isAdministrator():
        return True
    quser = Q(user=user) | Q(user=None, role__in=user.groups.all())
    return Permission.objects.filter(quser, permission_type__in=['Onsite', 'Administer']).filter(
        Permission.is_valid_qobject()).exists()


def printers_access(view):
    """ Like needs_onsite, for any program: logged in and can_use_printers
    (switching back from a morphed user who can't, as onsite pages do). """
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not can_use_printers(user):
            user.updateOnsite(request)
            old = user.get_old(request)
            if not user.other_user or not can_use_printers(old):
                return render_to_response('errors/program/notonsite.html', request, {})
            user.switch_back(request)
        return view(request, *args, **kwargs)
    return wrapper


def _json(data, status=200):
    return HttpResponse(json.dumps(data), content_type='application/json', status=status)


def _url(view=''):
    return BASE_URL + view


def _location(request):
    try:
        location_id = int(request.GET.get('location') or request.POST.get('location'))
    except (TypeError, ValueError):
        raise Http404
    location = Printer.objects.filter(id=location_id).first()
    if location is None:
        raise Http404
    return location


def _program(request):
    """ The program whose onsite page linked here (?program=<id>), remembered
    for this session, or None. """
    from esp.program.models import Program
    if request.GET.get('program'):
        try:
            request.session[SESSION_PROGRAM] = int(request.GET['program'])
        except ValueError:
            pass
    program_id = request.session.get(SESSION_PROGRAM)
    return Program.objects.filter(id=program_id).first() if program_id else None


@printers_access
def printers(request):
    """ The Printers page. """
    printing.default_location()
    printing.release_all_stale()
    locations = list(Printer.objects.active().order_by('-is_default', 'name'))
    for location in locations:
        location.connected = printing.is_connected(location)
        location.info = json.loads(location.network_info or '{}')
        location.settings = printing.location_settings(location)
        waiting = printing.jobs_for(location) if location.connected else \
            PrintRequest.objects.filter(printer=location, status='queued').order_by('id')
        location.waiting = waiting.count()
        oldest = waiting.first()
        location.oldest_waiting = oldest.time_requested if oldest else None
        location.history = location.changes.select_related('recorded_by')[:8]
        location.open_jobs = printing.open_jobs(location)
        location.recent_jobs = printing.recent_jobs(location)
    return render_to_response(TEMPLATES + 'printers.html', request, {
        'program': _program(request), 'locations': locations,
        'laptop_timeout': int(printing.LAPTOP_TIMEOUT.total_seconds()),
        'network_printing': print_server.configured(),
        'archived_locations': Printer.objects.filter(archived=True).order_by('name'),
    })


@printers_access
def printers_probe(request):
    """ Asks a network printer what it is, before connecting it (JSON). """
    try:
        (uri, info) = printing.probe(request.GET.get('address', ''))
    except printing.PrintingError as e:
        return _json({'error': str(e)})
    return _json({'uri': uri, 'info': info})


@printers_access
def printers_action(request):
    """ Changes to locations and their printers, from the Printers page. """
    if request.method != 'POST':
        raise Http404
    action = request.POST.get('action')
    try:
        recorded_by = dayof.real_user(request)
        take_over = bool(request.POST.get('take_over'))
        if action == 'add_location':
            name = (request.POST.get('name') or '').strip()
            if not name or Printer.objects.active().filter(name=name).exists():
                raise printing.PrintingError('Enter a new, unused location name.')
            location = Printer.objects.create(name=name[:255])
            printing.log(location, 'location added', '', recorded_by)
            messages.success(request, 'Added location %s.' % name)
            return HttpResponseRedirect(_url())
        location = _location(request)
        if action == 'connect':
            address = request.POST.get('address', '')
            (uri, info) = printing.probe(address)
            printing.connect_network(location, address, info, uri, recorded_by, take_over)
            if request.POST.get('discard_waiting'):
                printing.discard_waiting(location, recorded_by)
            messages.success(request, '%s now prints to %s (%s).' % (location.name, address, info['model']))
        elif action == 'disconnect':
            printing.disconnect(location, recorded_by)
            messages.success(request, 'Disconnected %s.' % location.name)
        elif action == 'test':
            job = printing.queue_test_page(location, recorded_by)
            ahead = len(printing.open_jobs(location)) - 1
            messages.success(request, 'Queued a test page for %s (job #%d)%s.' % (
                location.name, job.id, '; it prints after the %d job%s ahead of it' % (
                    ahead, '' if ahead == 1 else 's') if ahead > 0 else ''))
        elif action == 'settings':
            printing.save_settings(location, request.POST, recorded_by)
            messages.success(request, 'Saved the settings for %s.' % location.name)
        elif action == 'rename':
            name = (request.POST.get('name') or '').strip()
            if not name or Printer.objects.active().filter(name=name).exclude(id=location.id).exists():
                raise printing.PrintingError('Enter a new, unused location name.')
            with transaction.atomic():
                printing.log(location, 'renamed', '%s -> %s' % (location.name, name), recorded_by)
                location.name = name[:255]
                location.save()
        elif action == 'archive':
            printing.archive(location, recorded_by)
            messages.success(request, 'Archived location %s.' % location.name)
        elif action == 'restore':
            printing.restore(location, recorded_by)
            messages.success(request, 'Restored location %s.' % location.name)
        elif action == 'discard_waiting':
            count = printing.discard_waiting(location, recorded_by)
            messages.success(request, 'Cancelled %d waiting job(s) for %s.' % (count, location.name))
        else:
            raise Http404
    except printing.PrintingError as e:
        messages.error(request, str(e))
    return HttpResponseRedirect(_url())


@printers_access
def printers_laptop(request):
    """ This laptop prints for a location (claimed by the page's script). """
    location = _location(request)
    return render_to_response(TEMPLATES + 'laptop.html', request, {
        'program': _program(request), 'location': location,
        'connected_elsewhere': printing.is_connected(location),
        'printers_url': _url(), 'printers_base': BASE_URL,
    })


@printers_access
def printers_laptop_run(request):
    """ The page left running on the printing laptop, after it claimed
    the location on printers_laptop (the token is in the URL fragment). """
    location = _location(request)
    return render_to_response(TEMPLATES + 'laptop_running.html', request, {
        'program': _program(request), 'location': location,
        'printers_url': _url(), 'printers_base': BASE_URL,
    })


@printers_access
def printers_test_pdf(request):
    """ The test page, for a laptop to print from its browser (the same
    one network printers get). """
    location = _location(request)
    pdf = printing.test_page_pdf(location, dayof.real_user(request), 'this laptop')
    return HttpResponse(pdf, content_type='application/pdf')


@printers_access
def printers_claim(request):
    if request.method != 'POST':
        raise Http404
    location = _location(request)
    try:
        recorded_by = dayof.real_user(request)
        token = printing.claim_for_laptop(location, recorded_by,
                                          take_over=bool(request.POST.get('take_over')))
        if request.POST.get('discard_waiting'):
            printing.discard_waiting(location, recorded_by)
    except (printing.PrintingError, ESPError_NoLog) as e:
        return _json({'error': str(e)}, 409)
    return _json({'token': token})


@printers_access
def printers_poll(request):
    """ The laptop asks for its next job. """
    if request.method != 'POST':
        raise Http404
    location = _location(request)
    try:
        job = printing.next_job_for_laptop(location, request.POST.get('token', ''))
    except printing.PrintingError as e:
        return _json({'stop': str(e)}, 409)
    if job is None:
        return _json({'job': None})
    return _json({'job': job.id, 'title': job.describe(), 'copies': job.copies,
                  'pdf': '%s?%s' % (_url('printers_job_pdf'), urlencode({
                      'location': location.id, 'job': job.id, 'token': request.POST.get('token', '')}))})


@printers_access
def printers_job_pdf(request):
    location = _location(request)
    job = printing.laptop_job(location, request.GET.get('token', ''), request.GET.get('job') or 0)
    if job is None:
        raise Http404
    try:
        pdf = printing.render(job)
    except Exception as e:
        printing.mark_printed(job, ok=False, error='Could not make the document: %s' % e)
        raise
    return HttpResponse(pdf, content_type='application/pdf')


@printers_access
def printers_done(request):
    if request.method != 'POST':
        raise Http404
    location = _location(request)
    job = printing.laptop_job(location, request.POST.get('token', ''), request.POST.get('job') or 0)
    if job is not None:
        printing.mark_printed(job, ok=request.POST.get('ok') != '0', error=request.POST.get('error', ''))
        Printer.objects.filter(id=location.id).update(
            last_result='ok' if request.POST.get('ok') != '0' else 'failed', last_result_at=timezone.now())
    return _json({'ok': True})


@printers_access
def printers_release(request):
    """ The laptop stops printing (its Stop button). A laptop that just
    goes away is released after LAPTOP_TIMEOUT instead. """
    if request.method != 'POST':
        raise Http404
    location = _location(request)
    printing.release_laptop(location, request.POST.get('token', ''))
    return _json({'ok': True})


#   Most jobs one status request may ask about
MAX_STATUS_JOBS = 50


def printers_job_status(request):
    """ How the jobs in ?jobs=1,2,... are getting on (the print panel's live
    status, after it sends them). JSON {"jobs": [printing.job_progress]}.
    Polled, so unlike printers_access it never switches a morphed user back:
    the account behind the request (dayof.real_user) must be able to use
    the printers. """
    if not request.user.is_authenticated or not can_use_printers(dayof.real_user(request)):
        return _json({'error': 'You can\'t see print jobs.'}, 403)
    try:
        ids = [int(i) for i in request.GET.get('jobs', '').split(',') if i.strip()][:MAX_STATUS_JOBS]
    except ValueError:
        return _json({'error': 'Bad job ids.'}, 400)
    jobs = PrintRequest.objects.filter(id__in=ids).order_by('id')
    return _json({'jobs': [printing.job_progress(job) for job in jobs]})


#   /manage/printers/<view>
VIEWS = {view.__name__: view for view in (printers_probe, printers_action, printers_laptop, printers_laptop_run,
                                         printers_test_pdf, printers_claim, printers_poll, printers_job_pdf,
                                         printers_done, printers_release, printers_job_status)}


def dispatch(request, view):
    if view not in VIEWS:
        raise Http404
    return VIEWS[view](request)
