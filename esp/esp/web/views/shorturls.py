from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect

def resolve(request, tag):
    if tag not in settings.SHORTURLS:
        raise Http404()
    
    url = settings.SHORTURLS[tag]
    return redirect(url)
