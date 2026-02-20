from __future__ import absolute_import
import json
import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError
from django.dispatch import receiver
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from esp.formstack.signals import formstack_post_signal
from esp.program.models import Program
from esp.users.models import ESPUser

logger = logging.getLogger(__name__)

@csrf_exempt
def formstack_webhook(request):
    if request.method != 'POST':
        raise Http404

    data = request.POST.dict()
    expected_handshake = getattr(settings, 'FORMSTACK_HANDSHAKE_KEY', None)
    handshake_key = data.pop('HandshakeKey', None)

    if not expected_handshake:
        logger.warning('Blocked Formstack webhook because FORMSTACK_HANDSHAKE_KEY is not configured.')
        return HttpResponseForbidden("Formstack webhook is not configured.")
    if not handshake_key or not constant_time_compare(str(handshake_key), str(expected_handshake)):
        return HttpResponseForbidden("Invalid handshake key.")

    form_id = data.pop('FormID', None)
    submission_id = data.pop('UniqueID', None)
    if not form_id or not submission_id:
        return HttpResponseBadRequest("Missing required Formstack payload fields.")

    formstack_post_signal.send(sender=None, form_id=form_id, submission_id=submission_id, fields=data)
    return HttpResponse()

@csrf_exempt
@never_cache
@require_POST
def medicalsyncapi(request):
    """
    API for the medical form download script to get a list of students
    who *should* have turned in a medical form, to cross-check with the
    list of medical forms we actually have.

    The program name is specified by a string in the 'program' parameter.
    It should be formatted as "Spring HSSP 2013","Spark 2014", etc.

    Authentication is performed by username and password via the request
    parameters of those names. Access is restricted to Admins.
    """
    if not request.is_secure():
        return HttpResponseServerError("HTTPS is required when accessing this view")

    # Authenticate
    username = request.POST['username']
    password = request.POST['password']

    user = authenticate(username=username, password=password)
    if user is None or not user.isAdministrator():
        return HttpResponseForbidden("Authentication failed")

    # Find Program
    chunks = request.POST['program'].split(' ')
    if len(chunks) == 2:
        url = chunks[0] + '/' + chunks[1]
    elif len(chunks) == 3:
        url = chunks[1] + '/' + chunks[0] + '_' + chunks[2]
    else:
        return HttpResponseNotFound("Program could not be parsed")

    results = Program.objects.filter(url=url)

    if len(results) != 1:
        return HttpResponseNotFound("No/multiple programs match criteria")
    prog = results[0]

    # Collect Results
    students = prog.students()
    response = { 'submitted': dict(), 'bypass': dict() }
    for student in students['studentmedliab']:
        sid = student.id
        sname = student.last_name.capitalize() + ', ' + student.first_name.capitalize() + \
            ' (' + student.username + ' / ' + str(student.id) + ')'
        response['submitted'][sid] = sname
    for student in students['studentmedbypass']:
        sid = student.id
        sname = student.last_name.capitalize() + ', ' + student.first_name.capitalize() + \
            ' (' + student.username + ' / '+ str(student.id) + ')'
        response['bypass'][sid] = sname
    return HttpResponse(json.dumps(response), content_type='application/json')
