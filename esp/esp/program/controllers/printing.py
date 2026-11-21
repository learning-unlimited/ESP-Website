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

import io
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
#   A job that stopped the print server's queue twice waits behind the
#   others, and is tried again at most this often (see _queue_stopped)
REFUSED_RETRY = timedelta(minutes=5)
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
    _forget_refusals(loc)
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
    _forget_refusals(loc)
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
    _forget_refusals(loc)
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
        value = str(settings.get(key) or '').strip()
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
    raise PrintingError('No printer is currently connected for %s, so it wasn\'t sent. Connect a printer or a '
                        'laptop on the Printer Setup page, then try again.' % where)


def count_pages(pdf):
    """ The number of pages in a PDF (bytes), or None if it can't be read. """
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(pdf), strict=False).pages)
    except Exception:
        return None


def queue(kind, program, location=None, user=None, receipt=None, file=None, title='',
          requested_by=None, copies=1, settings=None, deposit_slip=None, document=None):
    """ Queues a job, refusing (PrintingError) if nothing would print it.
    What it prints: user's schedule, receipt, file (an uploaded PDF),
    deposit_slip, or document (what render_<kind> makes it from, e.g. a QR
    code sign's title, link and caption). settings: the job's own printer
    settings (see clean_settings). """
    if location is None:
        location = default_location()
    check_can_print(location)
    pages = None
    if file is not None:
        file.seek(0)
        pages = count_pages(file.read())
        file.seek(0)
    elif kind == 'test':
        pages = 2
    with transaction.atomic():
        job = PrintRequest.objects.create(kind=kind, program=program, printer=location, user=user, receipt=receipt,
                                          file=file, deposit_slip=deposit_slip, title=title[:200],
                                          document_json=json.dumps(document) if document else '',
                                          requested_by=requested_by, copies=copies, pages=pages,
                                          settings_json=json.dumps(settings) if settings else '')
        if kind in QUICK_TO_RENDER:
            #   (counts its pages; a document that can't be made isn't queued)
            try:
                render(job)
            except PrintingError:
                raise
            except Exception as e:
                logger.exception('Could not make print job %d', job.id)
                raise PrintingError('Could not make the document: %s' % e)
    return job


def queue_test_page(location, recorded_by):
    """ Queues the test page for whatever prints for the location (behind
    its waiting jobs, like anything else). """
    location = Printer.objects.get(id=location.id)
    if not is_connected(location):
        raise PrintingError('No printer is currently connected for %s, so there is nothing to test.' % location.name)
    job = queue('test', None, location, requested_by=recorded_by)
    log(location, 'test page queued', 'Job #%d.' % job.id, recorded_by)
    return job


def trouble_warning(job):
    """ A note for whoever queued the job if what will print it has trouble
    right now (blank if not). """
    location = job.printer if job.printer and is_connected(job.printer) else default_location()
    location = Printer.objects.get(id=location.id)
    if location.mode == 'network' and location.trouble:
        return '%s has trouble printing right now (%s); it will print once that clears.' % (
            location.name, location.trouble)
    if not is_connected(location):
        return 'No printer is currently connected for %s; it will print once one is.' % location.name
    return ''


#   The print panel (program/modules/dayof/print_panel.html): where to print,
#   that printer's settings, and (for some documents) copies

MAX_COPIES = 999


def print_panel_values(data, copies=True):
    """ (location, copies, settings, errors) from a print panel's fields in
    data (request.POST, or a JSON body). copies=False: always 1. Settings
    left blank keep the location's own. """
    errors = []
    location = Printer.objects.active().filter(id=_int(data.get('location'))).first()
    if location is None:
        errors.append('Choose where to print.')
    count = 1
    if copies:
        count = _int(data.get('copies') or 1)
        if not 1 <= count <= MAX_COPIES:
            errors.append('Copies must be from 1 to %d.' % MAX_COPIES)
    settings = {}
    if location is not None and location.mode == 'network':
        try:
            settings = clean_settings(location, data)
        except PrintingError as e:
            errors.append(str(e))
    return (location, count, settings, errors)


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def print_panel_locations():
    """ What the print panel shows for each location: whether something
    prints there, its trouble, and (network printers) what its printer can
    do and its own settings. """
    out = []
    for location in Printer.objects.active().order_by('-is_default', 'name'):
        info = json.loads(location.network_info or '{}') if location.mode == 'network' else {}
        out.append({
            'id': location.id, 'name': location.name, 'is_default': location.is_default,
            'connected': is_connected(location), 'mode': location.mode,
            'trouble': location.trouble if location.mode == 'network' else '',
            'capabilities': {key: info.get(capability, []) for (key, capability) in SETTING_CAPABILITIES}
            if location.mode == 'network' else {},
            'settings': location_settings(location) if location.mode == 'network' else {},
        })
    return out


def open_jobs(location):
    """ The jobs the location's printer has or will print (oldest first),
    for the Printers page: the one at the printer, then those waiting. A
    location with nothing connected lists its own waiting jobs (which the
    Default location prints). """
    if not is_connected(location):
        return list(PrintRequest.objects.filter(printer=location, status='queued').order_by('id').select_related(
            'printer', 'user', 'receipt', 'requested_by'))
    if location.mode == 'network':
        sent = _in_flight(location)
    else:
        sent = PrintRequest.objects.filter(status='sent', server_job=laptop_job_tag(location))
    jobs = list(sent.order_by('id').select_related('printer', 'user', 'receipt', 'requested_by'))
    waiting = jobs_for(location)
    if location.mode == 'network':
        waiting = waiting.order_by('refusals', 'id')     # (as the print worker sends them)
    jobs += list(waiting.select_related('printer', 'user', 'receipt', 'requested_by'))
    return jobs


def recent_jobs(location, count=20):
    """ The location's last finished jobs (printed, failed or cancelled),
    newest first, for the Printers page. """
    return list(PrintRequest.objects.filter(printer=location, status__in=('printed', 'failed', 'cancelled')).order_by(
        '-id').select_related('printer', 'user', 'receipt', 'requested_by')[:count])


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


def render_qr(job):
    from esp.program.controllers import qr_sign
    sign = json.loads(job.document_json)
    return qr_sign.sign_pdf(sign['title'], sign['link'], sign['caption'])


def render_deposit_slip(job):
    from esp.program.controllers import checkscan, checkscan_pdf
    if job.deposit_slip is None:
        raise PrintingError('The deposit slip is gone.')
    if job.deposit_slip.superseded_at is not None:
        #   (its set was discarded and prepared again since it was queued)
        raise PrintingError('This deposit slip was discarded; print a current one.')
    return checkscan_pdf.build(checkscan.slip_detail(job.deposit_slip))


def render_test(job):
    location = job.printer or default_location()
    how = {'network': 'network printer', 'laptop': 'laptop'}.get(location.mode, 'printer')
    return test_page_pdf(location, job.requested_by, how, job_settings(job))


#   To add a kind of document: a choice in PrintRequest.KIND_CHOICES and a
#   renderer here (a document made when queued is a file: render_pdf)
RENDERERS = {
    'schedule': render_schedule,
    'receipt': render_receipt,
    'pdf': render_pdf,
    'qr': render_qr,
    'deposit_slip': render_deposit_slip,
    'test': render_test,
}


#   Made in a moment, so queue() makes them once to count their pages
QUICK_TO_RENDER = ('qr', 'deposit_slip')


def render(job):
    pdf = RENDERERS[job.kind](job)
    if job.pages is None:
        pages = count_pages(pdf)
        if pages:
            PrintRequest.objects.filter(id=job.id).update(pages=pages)
            job.pages = pages
    return pdf


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
    now = timezone.now()
    Printer.objects.filter(id=location.id).update(
        last_result='ok' if ok else 'failed', last_result_at=now, last_error=error[:1000])
    if ok:
        Printer.objects.filter(id=location.id).update(last_ok_at=now)


def test_page_pdf(location, recorded_by, how, settings=None):
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
                'Settings: %s' % json.dumps(location_options(location, settings), sort_keys=True)
                if how == 'network printer' else '',
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
        #   Whatever prints it next starts afresh
        job.refusals = 0
        job.refused_at = None
        job.save()
        count += 1
    return count


def _forget_refusals(location):
    """ Whatever prints for the location changed: its jobs' refusals were
    by another printer, so they start afresh. """
    jobs_for(location).filter(refusals__gt=0).update(refusals=0, refused_at=None)


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
        _record_result(location, True)
        _set_trouble(location, '')
        return True
    if state['state'] in ('pending', 'held', 'processing', 'stopped') and state.get('printer_state') == 'stopped':
        return _queue_stopped(location, job, state)
    if state['state'] in ('canceled', 'aborted'):
        mark_printed(job, ok=False, error='The print server %s it (%s).' % (
            'cancelled' if state['state'] == 'canceled' else 'gave up on', ', '.join(state.get('reasons', []))))
        return True
    if job.time_executed and timezone.now() - job.time_executed > STUCK_AFTER:
        why = state.get('printer_message') or ', '.join(state.get('printer_reasons', [])) or \
            'it hasn\'t finished printing %s' % job.describe()
        _set_trouble(location, 'Printer: %s' % why)
    return False


def _queue_stopped(location, job, state):
    """ CUPS stopped the location's queue while printing job: its backend
    gave up on the printer (e.g. the printer dropped the connection partway
    through a large job), and CUPS then holds every job until the queue is
    re-enabled. Re-enables it (what disconnecting and reconnecting used to
    do) and decides what to do with the job. It's failed only when it must
    be the job, not the printer: it stopped the queue before, the printer
    printed something else since, and it stopped the queue again. A job
    that stops it twice waits behind the others (they show whether the
    printer works) and is tried again every REFUSED_RETRY. Returns whether
    the location is free for the next job. """
    name = print_server.queue_name(location)
    why = state.get('printer_message') or ', '.join(state.get('printer_reasons', [])) or 'the printer stopped'
    loc = Printer.objects.get(id=location.id)
    previous = job.refused_at
    printed_since = previous is not None and loc.last_ok_at is not None and loc.last_ok_at > previous
    refusals = job.refusals + 1
    if printed_since:
        print_server.cancel_job(name, job.server_job)
        changes = {'status': 'failed', 'error': 'The printer refused it %d times (%s), and printed other jobs in '
                   'between, so it\'s this document: it may be too large or complex for this printer (try fewer '
                   'copies, black and white, or another printer).' % (refusals, why)}
        outcome = 'failed it: the printer printed other jobs in between'
        free = True
    elif refusals >= 2:
        #   Maybe the job, maybe the printer: let the others go first
        print_server.cancel_job(name, job.server_job)
        changes = {'status': 'queued', 'server_job': '',
                   'error': 'The printer refused it %d times (%s); trying the other jobs first.' % (refusals, why)}
        outcome = 'moved it behind the other jobs'
        free = True
    else:
        #   CUPS sends it again once the queue is enabled
        changes = {'error': 'The printer refused it (%s); trying again.' % why}
        outcome = 'trying it again'
        free = False
    #   Only if it's still at the printer (not cancelled by staff meanwhile)
    PrintRequest.objects.filter(id=job.id, status='sent').update(refusals=refusals, refused_at=timezone.now(),
                                                                 **changes)
    #   If this fails, the next pass enables it before sending anything (or
    #   a job still there stops it again)
    _needs_enable.add(location.id)
    print_server.enable_queue(name)
    _needs_enable.discard(location.id)
    _record_result(location, False, 'The printer refused %s: %s' % (job.describe(), why))
    _set_trouble(location, 'Printer refused %s (%s); %s.' % (job.describe(), why, outcome))
    log(location, 'queue restarted', 'The printer refused %s (%s); %s.' % (job.describe(), why, outcome))
    return free


#   Locations whose stopped queue this worker couldn't re-enable yet
_needs_enable = set()


def _network_pass(location):
    """ One pass for a network location: checks on the job the print server
    has, and sends the next one once that has printed. Returns how many it
    sent. Raises PrintServerError if the print server fails. """
    if location.id in _needs_enable:
        print_server.enable_queue(print_server.queue_name(location))
        _needs_enable.discard(location.id)
    for job in _in_flight(location):
        if not _check_in_flight(location, job):
            return 0
    while True:
        with transaction.atomic():
            #   Jobs that stopped the queue twice go last, and wait a while between tries
            job = jobs_for(location).exclude(
                refusals__gte=2, refused_at__gt=timezone.now() - REFUSED_RETRY).order_by(
                'refusals', 'id').select_for_update(skip_locked=True).first()
            if job is None:
                if not jobs_for(location).exists():
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
            if not job.refusals:
                job.error = ''      # (a refused job keeps saying so until it's done)
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
