from django.http import HttpResponseRedirect

def redirect(request, target = '/', temp=''):
    return HttpResponseRedirect(target)
