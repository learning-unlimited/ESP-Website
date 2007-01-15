# Create your views here.
from esp.web.data import render_to_response
from esp.dblog.models import error


def ESPError(error_txt, log_extra = '', log_error = True):
    """  Log an error, and return a rendered error page """
    if log_error:
        error(error_txt, log_extra)

    return render_to_response('error.html', { 'error': error_txt } )
