"""Client for the print server (deploy/print_server/esp-print-server), which
does all network printing: it asks printers what they support, keeps a
driverless CUPS queue per day-of print location, and converts and prints
PDFs. The web server only talks HTTPS to it, with a bearer token:

    PRINT_SERVER = {                          # in local_settings.py
        'url': 'https://esp-print.mit.edu:8631',
        'token': '<the print server's /etc/esp-print/token>',
        'ca': '/path/to/cert.pem',            # optional: pin a self-signed certificate
    }

Without PRINT_SERVER, network printers can't be used (laptop printing still
works).
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import requests
from django.conf import settings

TIMEOUT = 60            # seconds; printing hands the job to CUPS and returns
ADD_TIMEOUT = 90        # creating a queue asks the printer, which can be slow
PROBE_TIMEOUT = 60      # an older printer also gets an SNMP lookup and a driver search


class PrintServerError(Exception):
    """ status is the print server's HTTP status, if it answered. """

    def __init__(self, message, status=None):
        super(PrintServerError, self).__init__(message)
        self.status = status

    @property
    def job_refused(self):
        """ Whether the print server refused the request itself (a bad job:
        an option it won't take, not a PDF, too large), so sending it again
        won't help, as opposed to being unreachable or failing (5xx), a
        missing queue (404, remade), or a wrong token (401, a setup problem). """
        return self.status is not None and 400 <= self.status < 500 and self.status not in (401, 404)


def configured():
    server = getattr(settings, 'PRINT_SERVER', None)
    return bool(server and server.get('url') and server.get('token'))


def queue_name(location):
    """ The queue on the print server for the location's network printer
    (shared by every site that uses it, so named by the connection's ULID,
    not the location's id). """
    if not location.queue_id:
        raise ValueError('%s has no network printer connected.' % location.name)
    return queue_name_for(location.queue_id)


def queue_name_for(queue_id):
    return 'esp-%s' % queue_id


def _request(method, path, timeout, **kwargs):
    if not configured():
        raise PrintServerError('Network printing isn\'t set up on this site (no PRINT_SERVER setting).')
    server = settings.PRINT_SERVER
    try:
        response = requests.request(method, server['url'].rstrip('/') + path, timeout=timeout,
                                    headers={'Authorization': 'Bearer %s' % server['token']},
                                    verify=server.get('ca') or True, **kwargs)
    except requests.exceptions.RequestException as e:
        raise PrintServerError('Couldn\'t reach the print server (%s).' % e.__class__.__name__)
    try:
        data = response.json()
    except ValueError:
        data = {}
    if response.status_code != 200:
        raise PrintServerError(data.get('error') or 'The print server answered HTTP %d.' % response.status_code,
                               response.status_code)
    return data


def probe(address):
    """ Asks the printer at address (an IP, a hostname, or an ipp(s):// URI)
    what it is and supports. Returns (uri, info). """
    data = _request('GET', '/probe', PROBE_TIMEOUT, params={'address': address})
    return (data['uri'], data['info'])


def add_queue(name, uri, description='', driver='everywhere'):
    """ Creates (or updates) the queue for the printer at uri, with the driver
    probe() chose for it ('everywhere' for driverless printing, or
    'model:<PPD>', 'postscript' or 'pcl' for older printers). Fails if the printer can't be
    reached. Returns what the queue supports (sides, color modes...: for an
    older printer, what its driver offers, which the printer itself doesn't
    say). """
    data = _request('PUT', '/queues/%s' % name, ADD_TIMEOUT,
                    json={'uri': uri, 'description': description[:100] or name, 'driver': driver or 'everywhere'})
    return data.get('info') or {}


def remove_queue(name):
    """ Deletes the queue and its waiting jobs; fine if it's already gone. """
    try:
        _request('DELETE', '/queues/%s' % name, TIMEOUT)
    except PrintServerError:
        pass


def print_pdf(name, pdf, title='', options=None):
    """ Prints a PDF on the queue. Returns CUPS's job id (e.g.
    'esp-01jd3k8w6p0b2c4d5e6f7g8h9j-12'). options are IPP job attributes, such as
    {'sides': 'two-sided-long-edge'}. """
    options = ['%s=%s' % (key, value) for (key, value) in sorted((options or {}).items())]
    data = _request('POST', '/queues/%s/jobs' % name, TIMEOUT, data=pdf,
                    params={'title': (title or 'ESP')[:100], 'o': options})
    return data.get('job', '')


def queue_missing(error):
    message = str(error)
    return 'does not exist' in message or 'Invalid destination' in message or 'not found' in message.lower()


def job_status(name, job):
    """ What the print server's CUPS says about a job (see esp-print-server):
    {'state': 'pending|held|processing|stopped|canceled|aborted|completed',
    'reasons': [...], 'printer_reasons': [...], 'printer_message': '...'}.
    Raises PrintServerError (with 'CUPS has no job' if it's gone). """
    return _request('GET', '/queues/%s/jobs/%s' % (name, job), PROBE_TIMEOUT)


def enable_queue(name):
    """ Restarts a queue CUPS stopped (its printer failed a job), so it
    prints its jobs again. """
    _request('POST', '/queues/%s/enable' % name, TIMEOUT)


def cancel_job(name, job):
    """ Cancels a job in the print server's CUPS; fine if it already finished. """
    _request('DELETE', '/queues/%s/jobs/%s' % (name, job), TIMEOUT)
