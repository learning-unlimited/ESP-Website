from django.http import HttpResponseRedirect

def simple_redirect(request, target = '/', temp=''):
    return HttpResponseRedirect(target)
