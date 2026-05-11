import datetime
from esp.utils.web import render_to_response
from esp.dbmail.models import MessageRequest, TextOfEmail
from esp.program.modules.handlers.commmodule import CommModule
from esp.users.models import admin_required
from argcache import cache_function

@cache_function
def get_email_data(start_date):
    requests = MessageRequest.objects.filter(created_at__gte=start_date).order_by('-created_at')

    requests_list = []
    for req in requests:
        toes = TextOfEmail.objects.filter(created_at=req.created_at,
                                          subject = req.subject,
                                          send_from = req.sender)
        if req.processed:
            req.num_rec = toes.count()
        else:
            req.num_rec = CommModule.approx_num_of_recipients(req.recipients, req.get_sendto_fn())
        req.num_sent = toes.filter(sent__isnull=False).count()
        if req.num_rec == req.num_sent:
            last_email = toes.order_by('-sent').first()
            if last_email is not None:
                req.finished_at = last_email.sent
            else:
                req.finished_at = "(Not finished)"
        else:
            req.finished_at = "(Not finished)"
        requests_list.append(req)
    return requests_list

get_email_data.depend_on_model(MessageRequest)
get_email_data.depend_on_model(TextOfEmail)

@admin_required
def emails(request):
    """
    View that displays information for recent email requests.
    GET data:
      'start_date' (optional):  Starting date to filter email requests by.
                                Should be given in the format "%m/%d/%Y".
    """
    context = {}
    if request.GET and "start_date" in request.GET:
        start_date = datetime.datetime.strptime(request.GET["start_date"], "%Y-%m-%d")
    else:
        start_date = datetime.date.today() - datetime.timedelta(30)
    context['start_date'] = start_date

    context['requests'] = get_email_data(start_date)

    return render_to_response('admin/emails.html', request, context)
