from django.http import HttpResponse, Http404
from django.dispatch import receiver
from django.views.decorators.csrf import csrf_exempt
from esp.formstack.signals import formstack_post_signal

@csrf_exempt
def formstack_webhook(request):
    if request.method == 'POST':
        data = request.POST.dict()
        form_id = data.pop('FormID')
        submission_id = data.pop('UniqueID')
        handshake_key = data.pop('HandshakeKey', None)
        # TODO: verify handshake key
        formstack_post_signal.send(sender=None, form_id=form_id, submission_id=submission_id, fields=data)
        return HttpResponse()
    else:
        raise Http404
