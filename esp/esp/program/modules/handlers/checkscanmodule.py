"""Check scanning: scan paper checks, enter amounts, and prepare bank deposit slips.

The treasurer's browser talks to a network check scanner directly (Digital Check SSX1, SecureLink API),
encrypts the original images and MICR line to the treasurer's OpenPGP key and uploads only the
ciphertext plus a redacted front image and the rear image.  The business rules are in
``esp.program.controllers.checkscan``; this module is the pages and the JSON API behind them.

URLs are ``/onsite/<program>/<view>/<extra>`` with a single-token ``extra``, so each page and each API
resource is its own view and the operation travels in the request method, a ``?op=`` parameter or the
JSON body.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import functools
import json

from django.http import HttpResponse

from esp.program.controllers import checkscan as cs
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.utils.web import render_to_response

NO_CACHE = 'private, no-cache'


def _json(data, status=200):
    resp = HttpResponse(json.dumps(data), content_type='application/json', status=status)
    resp['Cache-Control'] = 'private, no-store'
    return resp


def _body(request):
    if not request.body:
        return {}
    try:
        body = json.loads(request.body.decode('utf-8'))
    except ValueError:
        raise cs.CheckScanError(400, 'request body is not valid JSON')
    if not isinstance(body, dict):
        raise cs.CheckScanError(400, 'request body must be a JSON object')
    return body


def _api(view):
    """Turn a CheckScanError raised by a view into a JSON error response."""
    @functools.wraps(view)
    def wrapper(self, request, *args, **kwargs):
        try:
            return view(self, request, *args, **kwargs)
        except cs.CheckScanError as e:
            return _json(dict(e.extra, error=e.message), e.status)
    return wrapper


def _not_allowed():
    raise cs.CheckScanError(405, 'method not allowed')


class CheckScanModule(ProgramModuleObj):
    doc = """Scan checks with the treasurer's check scanner, record their amounts, and prepare deposit slips."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Check Scanning",
            "link_title": "Scan Checks",
            "module_type": "onsite",
            "seq": 40,
            "choosable": 1,
            }

    # The default isStep() (True) is what lists this module under "Other Modules" on the onsite page.

    # ------------------------------------------------------------ pages
    # Each page is a template plus a script that calls the API views below.  The template sets <base href>
    # to the program's onsite URL, so the scripts use short relative URLs like "checkscan_api_batches/<id>".

    def _page(self, request, prog, name, batch_id=''):
        context = {'program': prog, 'base_url': '/onsite/%s/' % prog.url, 'batch_id': batch_id,
                   'insecure_dev_key': cs.private_key_on_server()}
        return render_to_response(self.baseDir() + name + '.html', request, context)

    @main_call
    @needs_admin
    def checkscan(self, request, tl, one, two, module, extra, prog):
        """Step 1: choose or start a batch."""
        return self._page(request, prog, 'index')

    @aux_call
    @needs_admin
    def checkscan_batch(self, request, tl, one, two, module, extra, prog):
        """Step 2: scan checks and enter amounts."""
        return self._page(request, prog, 'batch', extra)

    @aux_call
    @needs_admin
    def checkscan_finalize(self, request, tl, one, two, module, extra, prog):
        """Step 3: finalize the batch."""
        return self._page(request, prog, 'finalize', extra)

    @aux_call
    @needs_admin
    def checkscan_slips(self, request, tl, one, two, module, extra, prog):
        """Step 4: deposit slips."""
        return self._page(request, prog, 'slips', extra)

    @aux_call
    @needs_admin
    def checkscan_history(self, request, tl, one, two, module, extra, prog):
        return self._page(request, prog, 'history')

    # ------------------------------------------------------------ API

    @aux_call
    @needs_admin
    @_api
    def checkscan_api_info(self, request, tl, one, two, module, extra, prog):
        """GET: what the pages need to know that isn't a batch (the amount buttons, the user's name)."""
        if request.method != 'GET':
            _not_allowed()
        return _json({'program_name': prog.niceName(), 'user': request.user.username,
                      'amounts': cs.amount_buttons(prog), 'treasurer_name': cs.treasurer_name(request.user)})

    @aux_call
    @needs_admin
    @_api
    def checkscan_api_key(self, request, tl, one, two, module, extra, prog):
        """GET: the treasurer's OpenPGP public key, which the browser encrypts scans to."""
        if request.method != 'GET':
            _not_allowed()
        try:
            with open(cs.public_key_file()) as f:
                key = f.read()
        except IOError:
            raise cs.CheckScanError(404, "the treasurer's public key isn't installed on this server")
        return HttpResponse(key, content_type='text/plain')

    @aux_call
    @needs_admin
    @_api
    def checkscan_api_batches(self, request, tl, one, two, module, extra, prog):
        """GET [id]: list or detail.  POST: new batch.  PATCH id: edit the note.
        POST id ?op=archive|restore|finalize|reopen|slips|discard."""
        user, uid = request.user, extra
        if request.method == 'GET':
            return _json(cs.batch_detail(prog, uid) if uid else cs.list_batches(prog))
        if request.method == 'POST' and not uid:
            b = cs.create_batch(user, prog, _body(request).get('note'))
            return _json({'id': b.uid, 'program_name': prog.niceName(), 'program_batch': b.number}, 201)
        if not uid:
            _not_allowed()
        if request.method == 'PATCH':
            body = _body(request)
            if 'note' not in body:
                raise cs.CheckScanError(400, 'nothing to update')
            cs.update_note(user, prog, uid, body['note'])
            return _json(cs.batch_detail(prog, uid))
        if request.method != 'POST':
            _not_allowed()
        op = request.GET.get('op')
        simple = {'archive': cs.archive_batch, 'restore': cs.restore_batch,
                  'finalize': cs.finalize_batch, 'reopen': cs.reopen_batch}
        if op in simple:
            simple[op](user, prog, uid)
            return _json(cs.batch_detail(prog, uid))
        if op == 'slips':
            return _json({'ids': cs.create_slips(user, prog, uid, _body(request))}, 201)
        if op == 'discard':
            return _json({'discarded': cs.discard_slips(user, prog, uid)})
        raise cs.CheckScanError(400, 'unknown operation')

    @aux_call
    @needs_admin
    @_api
    def checkscan_api_checks(self, request, tl, one, two, module, extra, prog):
        """extra = batch id.  GET: the batch's checks.  POST (multipart): one scanned check."""
        if request.method == 'GET':
            return _json(cs.list_checks(prog, extra))
        if request.method == 'POST':
            if int(request.META.get('CONTENT_LENGTH') or 0) > cs.MAX_UPLOAD:
                raise cs.CheckScanError(400, 'upload too large')
            c = cs.upload_check(request.user, prog, extra, request.POST, request.FILES)
            return _json(cs.one_check(c), 201)
        _not_allowed()

    @aux_call
    @needs_admin
    @_api
    def checkscan_api_check(self, request, tl, one, two, module, extra, prog):
        """extra = check id.  PATCH: edit.  GET ?file=redacted|rear: an unencrypted image."""
        if request.method == 'PATCH':
            return _json(cs.update_check(request.user, prog, extra, _body(request)))
        if request.method == 'GET':
            names = {'redacted': cs.REDACTED, 'rear': cs.REAR}
            if request.GET.get('file') not in names:
                raise cs.CheckScanError(400, 'file must be redacted or rear')
            with open(cs.check_file(prog, extra, names[request.GET['file']]), 'rb') as f:
                resp = HttpResponse(f.read(), content_type='image/jpeg')
            resp['Cache-Control'] = NO_CACHE
            return resp
        _not_allowed()

    @aux_call
    @needs_admin
    @_api
    def checkscan_api_zip(self, request, tl, one, two, module, extra, prog):
        """extra = batch id.  GET: the batch's encrypted originals and MICR lines as a zip."""
        if request.method != 'GET':
            _not_allowed()
        data, name = cs.encrypted_zip(request.user, prog, extra)
        resp = HttpResponse(data, content_type='application/zip')
        resp['Content-Disposition'] = 'attachment; filename="%s"' % name
        return resp

    @aux_call
    @needs_admin
    @_api
    def checkscan_api_deposits(self, request, tl, one, two, module, extra, prog):
        """GET: slips (?batch=<id> to limit).  GET id: one slip's detail, or ?format=pdf|txt (&download=1).
        POST id ?op=print: print its PDF on a day-of print location (JSON body: the print panel's fields)."""
        if request.method == 'POST' and extra and request.GET.get('op') == 'print':
            return self._print_slip(request, prog, cs.get_slip(prog, extra))
        if request.method != 'GET':
            _not_allowed()
        if not extra:
            return _json(cs.list_slips(prog, request.GET.get('batch')))
        slip = cs.get_slip(prog, extra)
        fmt = request.GET.get('format')
        if not fmt:
            return _json(cs.slip_detail(slip))
        if fmt not in ('pdf', 'txt'):
            raise cs.CheckScanError(400, 'format must be pdf or txt')
        if fmt == 'pdf':
            from esp.program.controllers import checkscan_pdf
            resp = HttpResponse(checkscan_pdf.build(cs.slip_detail(slip)), content_type='application/pdf')
        else:
            resp = HttpResponse(cs.slip_text(slip), content_type='text/plain; charset=utf-8')
        resp['Content-Disposition'] = '%s; filename="%s"' % (
            'attachment' if request.GET.get('download') else 'inline', cs.slip_file_name(slip, fmt))
        resp['Cache-Control'] = NO_CACHE
        return resp

    @staticmethod
    def _print_slip(request, prog, slip):
        from esp.program.controllers import dayof, printing
        if slip.superseded_at is not None:
            raise cs.CheckScanError(409, 'this deposit slip was discarded; print a current one')
        (location, copies, settings, errors) = printing.print_panel_values(_body(request), copies=False)
        if errors:
            raise cs.CheckScanError(400, ' '.join(errors))
        detail = cs.slip_detail(slip)
        try:
            job = printing.queue('deposit_slip', prog, location, deposit_slip=slip,
                                 title='Deposit slip %d of %d (batch %d)' % (slip.slip_no, detail['n_in_set'],
                                                                         slip.batch.number),
                                 requested_by=dayof.real_user(request), settings=settings)
        except printing.PrintingError as e:
            raise cs.CheckScanError(409, str(e))
        cs.audit(request.user, 'deposit slip printed', slip=slip.uid, location=location.name, job=job.id)
        warning = printing.trouble_warning(job)
        return _json({'message': 'Sent %s to %s (job #%d).%s' % (job.describe(), location.name, job.id,
                                                                  ' ' + warning if warning else '')})

    class Meta:
        proxy = True
        app_label = 'modules'
