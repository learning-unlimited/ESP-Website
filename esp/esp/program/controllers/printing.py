"""Day-of printing: a queue of print requests (schedules, receipts, uploaded
PDFs), each for a location (esp.utils.models.Printer).

A location has at most one printer connected at a time:
  * a laptop running the printing page (Printers page, "Print from this
    laptop"), which polls for its location's jobs and prints them from the
    browser. It holds the location with a random token; it loses it when it
    stops, when someone takes over, or after LAPTOP_TIMEOUT without polling;
  * a network printer, which the print worker (manage.py print_worker) sends
    jobs to through the print server (esp.utils.print_server: CUPS on another
    machine, one queue per location).
The Default location takes requests that don't name a location, and also
the jobs of any location with nothing connected. Every connection change
goes through _locked(), which locks the location's row, and is logged as a
PrinterChange.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import logging
import re
import secrets
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.test import RequestFactory
from django.utils import timezone

from esp.utils import print_server
from esp.utils.models import Printer, PrinterChange, PrintRequest, new_ulid

logger = logging.getLogger(__name__)

LAPTOP_TIMEOUT = timedelta(seconds=60)
#   Network printers: a sent job not printed by then means the printer has
#   trouble (shown on the Printers page); after the print server fails, wait
#   this long before trying it again for that location
STUCK_AFTER = timedelta(seconds=90)
RETRY_AFTER = timedelta(seconds=20)
DEFAULT_NAME = 'Default'


class PrintingError(ValueError):
    pass


def default_location():
    location = Printer.objects.filter(is_default=True).first()
    if location is None:
        location = Printer.objects.create(name=DEFAULT_NAME, is_default=True)
    return location


def log(location, action, detail='', recorded_by=None):
    PrinterChange.objects.create(printer=location, action=action, detail=detail,
                                 recorded_by=recorded_by)


def laptop_is_live(location, now=None):
    now = now or timezone.now()
    return (location.mode == 'laptop' and location.laptop_last_seen is not None
            and now - location.laptop_last_seen <= LAPTOP_TIMEOUT)


def is_connected(location):
    """ Whether something is printing for this location right now. """
    if location.mode == 'network':
        return True
    return laptop_is_live(location)


def release_stale(location):
    """ Frees a location whose laptop stopped polling (closed, asleep, off
    the network). Returns True if it did. """
    with transaction.atomic():
        loc = Printer.objects.select_for_update().get(id=location.id)
        if loc.mode == 'laptop' and not laptop_is_live(loc):
            _clear(loc)
            loc.save()
            log(loc, 'auto-released', 'The laptop stopped checking in for %d seconds.'
                % LAPTOP_TIMEOUT.total_seconds())
            return True
    return False


def release_all_stale():
    for location in Printer.objects.filter(mode='laptop'):
        if not laptop_is_live(location):
            release_stale(location)


def _clear(loc):
    """ Forgets what's connected (callers remove a network printer's queue
    first). """
    loc.trouble = ''
    loc.trouble_since = None
    loc.mode = 'none'
    loc.queue_id = None
    loc.laptop_token = ''
    loc.laptop_claimed_by = None
    loc.laptop_last_seen = None


def _describe_connection(loc):
    if loc.mode == 'network':
        return 'network printer %s' % (loc.network_address or loc.network_uri)
    if loc.mode == 'laptop':
        who = loc.laptop_claimed_by.username if loc.laptop_claimed_by else ''
        return 'a laptop (%s)' % who if who else 'a laptop'
    return 'nothing'


def _locked(location_id, take_over):
    """ The location's row, locked; refuses if something is connected and
    take_over isn't set. """
    loc = Printer.objects.select_for_update().get(id=location_id)
    if loc.archived:
        raise PrintingError('%s is archived; restore it on the Printers page first.' % loc.name)
    if loc.mode == 'laptop' and not laptop_is_live(loc):
        _clear(loc)
    if loc.mode != 'none' and not take_over:
        raise PrintingError('%s already has %s connected; take over or disconnect it first.'
                            % (loc.name, _describe_connection(loc)))
    return loc


@transaction.atomic
def claim_for_laptop(location, recorded_by, take_over=False):
    """ This laptop starts printing for the location. Returns its token. """
    loc = _locked(location.id, take_over)
    previous = _describe_connection(loc)
    if loc.mode == 'network':
        _recall_network_jobs(loc)
        print_server.remove_queue(print_server.queue_name(loc))
    _clear(loc)
    loc.mode = 'laptop'
    loc.laptop_token = secrets.token_urlsafe(24)
    loc.laptop_claimed_by = recorded_by
    loc.laptop_last_seen = timezone.now()
    loc.save()
    log(loc, 'took over with a laptop' if previous != 'nothing' else 'laptop connected',
        'Replaced %s.' % previous if previous != 'nothing' else '', recorded_by)
    return loc.laptop_token


def probe(address):
    """ Asks the printer at address what it is and supports. Returns
    (uri, info dict); raises PrintingError if it can't be used. """
    try:
        return print_server.probe(address)
    except print_server.PrintServerError as e:
        raise PrintingError(str(e))


def default_settings(info):
    """ Sensible settings for a newly connected printer: double-sided if it
    can (schedules are 3 pages: 2 of schedule, 1 barcode page). """
    settings = {}
    if 'two-sided-long-edge' in info.get('sides', []):
        settings['sides'] = 'two-sided-long-edge'
    if 'monochrome' in info.get('color_modes', []):
        settings['color_mode'] = 'monochrome'
    return settings


@transaction.atomic
def connect_network(location, address, info, uri, recorded_by, take_over=False):
    loc = _locked(location.id, take_over or location.mode == 'network')
    previous = _describe_connection(loc)
    keep_settings = loc.mode == 'network' and loc.settings_json
    if 'driver' in info and not info['driver']:
        raise PrintingError('%s doesn\'t take anything the print server can send it (it accepts %s).' % (
            address.strip(), ', '.join(info.get('formats') or ['nothing it says'])))
    #   Each connection gets its own queue. Make the new one first, so a
    #   failure leaves what was connected as it was.
    queue_id = new_ulid()
    try:
        offered = print_server.add_queue(print_server.queue_name_for(queue_id), uri, loc.name, info.get('driver'))
    except print_server.PrintServerError as e:
        raise PrintingError('Couldn\'t set up %s for printing: %s' % (address.strip(), e))
    if loc.mode == 'network':
        _recall_network_jobs(loc)
        print_server.remove_queue(print_server.queue_name(loc))
    _clear(loc)
    loc.mode = 'network'
    loc.queue_id = queue_id
    loc.network_address = address.strip()
    loc.network_uri = uri
    loc.last_result = ''
    loc.last_error = ''
    #   An older printer doesn't say what it can do; its driver does
    info = dict(info)
    for key in ('sides', 'color_modes', 'qualities', 'media', 'scaling'):
        if not info.get(key) and offered.get(key):
            info[key] = offered[key]
    loc.network_info = json.dumps(info)
    if not keep_settings:
        loc.settings_json = json.dumps(default_settings(info))
    loc.save()
    detail = '%s at %s' % (info.get('model') or 'printer', loc.network_address)
    if previous != 'nothing':
        detail += '; replaced %s' % previous
    log(loc, 'network printer connected', detail, recorded_by)
    return loc


@transaction.atomic
def disconnect(location, recorded_by):
    loc = Printer.objects.select_for_update().get(id=location.id)
    previous = _describe_connection(loc)
    if loc.mode == 'network':
        _recall_network_jobs(loc)
        print_server.remove_queue(print_server.queue_name(loc))
    _clear(loc)
    loc.network_address = loc.network_uri = loc.network_info = ''
    loc.save()
    log(loc, 'disconnected', 'Was %s.' % previous, recorded_by)


@transaction.atomic
def archive(location, recorded_by):
    """ Hides a location (instead of deleting it, which would lose its
    history and print requests), disconnecting whatever prints for it. """
    loc = Printer.objects.select_for_update().get(id=location.id)
    if loc.is_default:
        raise PrintingError('The Default location can\'t be archived.')
    if PrintRequest.objects.filter(printer=loc, status__in=['queued', 'sent']).exists():
        raise PrintingError('%s has jobs waiting; cancel them first.' % loc.name)
    if loc.mode != 'none':
        disconnect(loc, recorded_by)
        loc.refresh_from_db()
    loc.archived = True
    loc.save()
    log(loc, 'archived', '', recorded_by)


@transaction.atomic
def restore(location, recorded_by):
    loc = Printer.objects.select_for_update().get(id=location.id)
    if Printer.objects.active().filter(name=loc.name).exclude(id=loc.id).exists():
        raise PrintingError('Another location is called %s; rename that one first.' % loc.name)
    loc.archived = False
    loc.save()
    log(loc, 'restored', '', recorded_by)


@transaction.atomic
def release_laptop(location, token):
    loc = Printer.objects.select_for_update().get(id=location.id)
    if loc.mode == 'laptop' and token and loc.laptop_token == token:
        _clear(loc)
        loc.save()
        log(loc, 'laptop stopped printing')
        return True
    return False


#   Option values the print server accepts (its OPTION pattern)
SETTING_VALUE = re.compile(r'^[A-Za-z0-9._-]{1,60}$')


#   Each setting, and the printer capability (in network_info) listing its values
SETTING_CAPABILITIES = (('sides', 'sides'), ('color_mode', 'color_modes'), ('quality', 'qualities'),
                        ('media', 'media'), ('scaling', 'scaling'))


def clean_settings(location, settings):
    """ The non-blank settings (a dict like the settings form's fields),
    checked against what the location's printer can do; raises
    PrintingError otherwise. """
    info = json.loads(location.network_info or '{}')
    clean = {}
    for (key, capability) in SETTING_CAPABILITIES:
        value = (settings.get(key) or '').strip()
        if value:
            if value not in info.get(capability, []):
                raise PrintingError('This printer doesn\'t support %s = %s.' % (key, value))
            if not SETTING_VALUE.match(value):
                #   (what the print server accepts as an option value)
                raise PrintingError('%s = %s can\'t be sent to the print server.' % (key, value))
            clean[key] = value
    return clean


@transaction.atomic
def save_settings(location, settings, recorded_by):
    loc = Printer.objects.select_for_update().get(id=location.id)
    clean = clean_settings(loc, settings)
    old = loc.settings_json
    loc.settings_json = json.dumps(clean)
    loc.save()
    log(loc, 'settings changed', '%s -> %s' % (old or '{}', loc.settings_json), recorded_by)
    return clean


def location_settings(location):
    try:
        return json.loads(location.settings_json or '{}')
    except ValueError:
        return {}


#   Settings as IPP job attributes (lp -o name=value)
QUALITY = {'draft': 3, 'normal': 4, 'high': 5}     # print-quality enum values
SETTING_OPTIONS = {'sides': 'sides', 'color_mode': 'print-color-mode', 'media': 'media',
                   'scaling': 'print-scaling'}


def job_settings(job):
    try:
        return json.loads(job.settings_json or '{}')
    except ValueError:
        return {}


def location_options(location, overrides=None):
    """ The location's settings as print options, with overrides (a job's
    own settings) over them, skipping any the location's printer can't do
    (e.g. a job for another location that Default is printing). """
    settings = location_settings(location)
    info = json.loads(location.network_info or '{}')
    for (key, capability) in SETTING_CAPABILITIES:
        value = (overrides or {}).get(key)
        if value and value in info.get(capability, []) and SETTING_VALUE.match(value):
            settings[key] = value
    options = {SETTING_OPTIONS[key]: value for (key, value) in settings.items() if key in SETTING_OPTIONS and value}
    if settings.get('quality') in QUALITY:
        options['print-quality'] = QUALITY[settings['quality']]
    return options


#   The queue

def check_can_print(location=None):
    """ Raises PrintingError unless something will print a job sent to
    location (None: Default): its own printer, or Default's. """
    default = default_location()
    #   What's connected right now, not what the caller's copy says
    location = Printer.objects.get(id=location.id) if location is not None else default
    if location.archived:
        raise PrintingError('%s is archived; choose another location.' % location.name)
    if is_connected(location) or is_connected(default):
        return
    where = 'Default' if location.is_default else '%s or Default' % location.name
    raise PrintingError('Nothing is printing for %s right now, so it wasn\'t sent. Connect a printer or a laptop '
                        'on the Printers page, then try again.' % where)


def queue(kind, program, location=None, user=None, receipt=None, file=None, title='',
          requested_by=None, copies=1, settings=None):
    """ Queues a job, refusing (PrintingError) if nothing would print it.
    settings: the job's own printer settings (see clean_settings). """
    if location is None:
        location = default_location()
    check_can_print(location)
    return PrintRequest.objects.create(kind=kind, program=program, printer=location, user=user, receipt=receipt,
                                       file=file, title=title[:200], requested_by=requested_by, copies=copies,
                                       settings_json=json.dumps(settings) if settings else '')


def jobs_for(location):
    """ Queued jobs this location's printer should print, oldest first: its
    own, plus, for the Default location, those of every location with
    nothing connected (and old requests with no location). """
    q = Q(printer=location)
    if location.is_default:
        unattended = [loc.id for loc in Printer.objects.active().exclude(id=location.id) if not is_connected(loc)]
        q |= Q(printer__isnull=True) | Q(printer__in=unattended)
    return PrintRequest.objects.filter(q, status='queued').order_by('id')


@transaction.atomic
def next_job_for_laptop(location, token):
    """ For a laptop's poll: checks it still holds the location (raises
    PrintingError saying who took over if not), records that it's alive,
    and hands it the next job (marked sent), or None. """
    loc = Printer.objects.select_for_update().get(id=location.id)
    if loc.mode != 'laptop' or not token or loc.laptop_token != token:
        change = loc.changes.first()
        who = ''
        if change is not None:
            who = ' by %s at %s' % (change.recorded_by.username if change.recorded_by else 'someone',
                                    change.timestamp.strftime('%H:%M'))
        raise PrintingError('This laptop is no longer printing for %s (taken over or disconnected%s).'
                            % (loc.name, who))
    loc.laptop_last_seen = timezone.now()
    loc.save(update_fields=['laptop_last_seen'])
    job = jobs_for(loc).select_for_update(skip_locked=True).first()
    if job is not None:
        job.status = 'sent'
        job.attempts += 1
        job.time_executed = timezone.now()
        job.server_job = laptop_job_tag(loc)
        job.save()
    return job


def laptop_job_tag(location):
    """ Marks a job as sent to this location's laptop (in server_job, which
    network jobs use for CUPS's job id), so only that laptop can fetch it or
    report it done. """
    return 'laptop-%d' % location.id


def laptop_job(location, token, job_id):
    """ The job this location's laptop (holding token) was sent, or None. """
    if not token or location.mode != 'laptop' or location.laptop_token != token:
        return None
    return PrintRequest.objects.filter(id=job_id, status='sent', server_job=laptop_job_tag(location)).select_related(
        'program', 'user').first()


def mark_printed(job, ok=True, error=''):
    job.status = 'printed' if ok else 'failed'
    job.error = error
    if ok:
        job.time_executed = timezone.now()
    job.save()
    if ok:
        discard_upload(job)


#   An uploaded PDF is deleted once it prints, or a day after its job failed
#   or was cancelled (to see what went wrong); the job's record stays
UPLOAD_KEEP = timedelta(days=1)


def discard_upload(job):
    """ Deletes the job's uploaded file, unless another waiting job still
    needs it. """
    if not job.file:
        return
    name = job.file.name
    if not PrintRequest.objects.filter(file=name, status__in=('queued', 'sent')).exclude(id=job.id).exists():
        job.file.storage.delete(name)
        PrintRequest.objects.filter(file=name).exclude(status__in=('queued', 'sent')).update(file='')


def discard_old_uploads():
    """ Deletes uploads of jobs that ended (failed or cancelled) over
    UPLOAD_KEEP ago. """
    old = timezone.now() - UPLOAD_KEEP
    for job in PrintRequest.objects.filter(kind='pdf', status__in=('failed', 'cancelled', 'printed'),
                                           time_requested__lt=old).exclude(file='').exclude(file__isnull=True):
        discard_upload(job)


@transaction.atomic
def discard_waiting(location, recorded_by):
    """ "Start fresh": cancels the location's queued jobs (e.g. left over from
    an earlier session). Returns how many. """
    count = _recall_network_jobs(location, cancel=True)
    count += PrintRequest.objects.filter(printer=location, status='queued').update(status='cancelled')
    if count:
        log(location, 'discarded old jobs', '%d waiting jobs cancelled.' % count, recorded_by)
    return count


#   Rendering a job as PDF

def _fake_request():
    request = RequestFactory().get('/')
    request.session = {}
    return request


def render_schedule(job):
    from esp.program.modules.handlers.programprintables import ProgramPrintables
    response = ProgramPrintables.get_student_schedules(_fake_request(), [job.user], job.program, extra='pdf')
    return response.content


def render_receipt(job):
    from esp.program.controllers.receipts import receipt_pdf
    return receipt_pdf(job.receipt)


def render_pdf(job):
    job.file.open('rb')
    try:
        return job.file.read()
    finally:
        job.file.close()


#   To add a kind of document: a choice in PrintRequest.KIND_CHOICES and a
#   renderer here
RENDERERS = {
    'schedule': render_schedule,
    'receipt': render_receipt,
    'pdf': render_pdf,
}


def render(job):
    return RENDERERS[job.kind](job)


#   Network printing (the print worker)

def send_to_network_printer(location, pdf, job_name, copies=1, settings=None):
    """ Hands the PDF to the location's CUPS queue (remaking the queue if it
    has gone, e.g. the print server was rebuilt), with the location's
    settings and, over them, settings (the job's own). Raises
    print_server.PrintServerError. """
    name = print_server.queue_name(location)
    options = location_options(location, settings)
    if copies > 1:
        options['copies'] = copies
    try:
        return print_server.print_pdf(name, pdf, job_name, options)
    except print_server.PrintServerError as e:
        if not print_server.queue_missing(e) or not location.network_uri:
            raise
    info = json.loads(location.network_info or '{}')
    print_server.add_queue(name, location.network_uri, location.name, info.get('driver'))
    return print_server.print_pdf(name, pdf, job_name, options)


def _record_result(location, ok, error=''):
    Printer.objects.filter(id=location.id).update(
        last_result='ok' if ok else 'failed', last_result_at=timezone.now(), last_error=error[:1000])


def test_page_pdf(location, recorded_by, how):
    """ A two-page test: printed two-sided, page 2 should be on the back of
    page 1, the same way up. how says what printed it. """
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    import io
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=letter)
    (width, height) = letter
    for (number, heading, lines) in (
            (1, 'Test page: %s' % location.name, [
                'Printed %s by %s' % (how, recorded_by.username if recorded_by else 'unknown'),
                'Sent %s' % timezone.now().strftime('%Y-%m-%d %H:%M'),
                'Settings: %s' % (location.settings_json or '{}') if how == 'network printer' else '',
                'If this page is two-sided, the back should read the same way up.']),
            (2, 'Back of the test page', [
                'If you can read this the right way up after turning the sheet over',
                'like a book page, two-sided printing is set up correctly.'])):
        c.setFont('Helvetica-Bold', 28)
        c.drawString(72, height - 100, heading)
        c.setFont('Helvetica', 14)
        y = height - 140
        for line in lines:
            if line:
                c.drawString(72, y, line)
                y -= 22
        c.setFont('Helvetica', 11)
        c.drawString(72, 52, 'Page %d of 2. The box should be whole: if an edge is cut off, check the paper size.' % number)
        c.rect(36, 36, width - 72, height - 72)
        c.showPage()
    c.save()
    return out.getvalue()


def test_page(location, recorded_by):
    """ Sends the test page to a network printer. """
    try:
        send_to_network_printer(location, test_page_pdf(location, recorded_by, 'network printer'), 'Test page')
    except print_server.PrintServerError as e:
        _record_result(location, False, str(e))
        log(location, 'test page failed', str(e), recorded_by)
        raise PrintingError('The test page failed: %s' % e)
    _record_result(location, True)
    log(location, 'test page sent', '', recorded_by)


def _in_flight(location):
    """ The location's job at the print server, waiting for CUPS to print it
    (at most one; its CUPS job id starts with the queue's name). """
    return PrintRequest.objects.filter(status='sent', server_job__startswith=print_server.queue_name(location) + '-')


def _recall_network_jobs(location, cancel=False):
    """ Takes the location's job back from the print server (on take-over,
    disconnect, or "cancel all waiting"): cancels it there and puts it back
    in the queue, or cancels it. Returns how many. """
    name = print_server.queue_name(location)
    count = 0
    for job in _in_flight(location):
        try:
            print_server.cancel_job(name, job.server_job)
        except print_server.PrintServerError:
            pass    # unreachable, or the queue is about to be deleted anyway
        job.status = 'cancelled' if cancel else 'queued'
        job.server_job = ''
        job.save()
        count += 1
    return count


def _set_trouble(location, message):
    """ Shows (or, with no message, clears) what stops a network location
    printing, keeping the time it started. """
    if message:
        Printer.objects.filter(id=location.id, trouble_since__isnull=True).update(trouble_since=timezone.now())
        Printer.objects.filter(id=location.id).update(trouble=message[:1000])
    else:
        Printer.objects.filter(id=location.id).exclude(trouble='', trouble_since__isnull=True).update(
            trouble='', trouble_since=None)


def _check_in_flight(location, job):
    """ Asks the print server about the job it has; returns whether the
    location is free for the next one. Raises PrintServerError if the print
    server can't be asked. """
    try:
        state = print_server.job_status(print_server.queue_name(location), job.server_job)
    except print_server.PrintServerError as e:
        if 'CUPS has no job' not in str(e):
            raise
        #   CUPS lost it (its queue was re-created, or the print server
        #   rebuilt): send it again
        job.status = 'queued'
        job.server_job = ''
        job.error = 'The print server lost this job; sending it again.'
        job.save()
        return True
    if state['state'] == 'completed':
        mark_printed(job)
        _set_trouble(location, '')
        return True
    if state['state'] in ('canceled', 'aborted'):
        mark_printed(job, ok=False, error='The print server %s it (%s).' % (
            'cancelled' if state['state'] == 'canceled' else 'gave up on', ', '.join(state.get('reasons', []))))
        return True
    if job.time_executed and timezone.now() - job.time_executed > STUCK_AFTER:
        why = state.get('printer_message') or ', '.join(state.get('printer_reasons', [])) or \
            'it hasn\'t finished printing %s' % job.describe()
        _set_trouble(location, 'Printer: %s' % why)
    return False


def _network_pass(location):
    """ One pass for a network location: checks on the job the print server
    has, and sends the next one once that has printed. Returns how many it
    sent. Raises PrintServerError if the print server fails. """
    for job in _in_flight(location):
        if not _check_in_flight(location, job):
            return 0
    while True:
        with transaction.atomic():
            job = jobs_for(location).select_for_update(skip_locked=True).first()
            if job is None:
                _set_trouble(location, '')
                return 0
            job.status = 'sent'
            job.attempts += 1
            job.time_executed = timezone.now()
            job.server_job = ''
            job.save()
        try:
            pdf = render(job)
        except Exception as e:
            logger.exception('Could not make print job %d', job.id)
            mark_printed(job, ok=False, error='Could not make the document: %s' % e)
            continue
        try:
            server_job = send_to_network_printer(location, pdf, job.describe(), copies=job.copies,
                                                 settings=job_settings(job))
        except print_server.PrintServerError as e:
            if e.job_refused:
                #   This job is the problem (e.g. an option the print server
                #   won't take): fail it and go on to the next
                mark_printed(job, ok=False, error='The print server refused it: %s' % e)
                _record_result(location, False, 'The print server refused %s: %s' % (job.describe(), e))
                continue
            #   Keep it waiting: outages never fail jobs
            job.status = 'queued'
            job.error = str(e)
            job.save()
            raise
        if server_job:
            job.server_job = server_job
            job.error = ''
            job.save()
        else:
            mark_printed(job)       # no job id to follow up on
        _set_trouble(location, '')
        return 1


#   When the print server last failed, per location (this worker process)
_retry_at = {}


def run_network_jobs_once():
    """ One pass of the print worker over the network locations: each has at
    most one job at the print server at a time, and a job counts as printed
    only once CUPS says so, so when the print server or the printer is down
    the jobs wait here (and staff can see them, cancel them, or take the
    location over with a laptop). Returns how many it sent. """
    release_all_stale()
    sent = 0
    now = timezone.now()
    for location in Printer.objects.active().filter(mode='network'):
        if _retry_at.get(location.id, now) > now:
            continue
        try:
            sent += _network_pass(location)
            _retry_at.pop(location.id, None)
        except print_server.PrintServerError as e:
            logger.warning('Print server trouble for %s: %s', location.name, e)
            _set_trouble(location, 'Print server: %s' % e)
            _retry_at[location.id] = now + RETRY_AFTER
    return sent
