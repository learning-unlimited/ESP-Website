from django.core.cache import cache
from django.core.mail import mail_admins
from esp.utils.web import render_to_response
from esp.users.models import admin_required

@admin_required
def flushcache(request):
    context = {}
    if request.POST:
        if "reason" in request.POST and len(request.POST['reason']) > 5:
            reason = request.POST['reason']
            _cache = cache
            while hasattr(_cache, "_wrapped_cache"):
                _cache = _cache._wrapped_cache
            if hasattr(_cache, "clear"):
                _cache.clear()
                mail_admins("Cache Flushed on server '%s'!" % request.META['SERVER_NAME'], "The cache was flushed by %s!  The following reason was given:\n\n%s" % (request.user.username, reason))
                context['success'] = "Cache Cleared."
            else:
                context['error'] = "Error: This cache backend doesn't support the 'clear' method.  Sorry; you'll have to flush this one manually."
        else:
            context['error'] = "Sorry, that doesn't count as a reason."

    return render_to_response('admin/cache_flush.html', request, context)
