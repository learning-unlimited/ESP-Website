import pytz
from django.utils import timezone
from esp.program.models import Program

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        program = None
        
        # Try to get program from view kwargs (passed by main.program)
        one = view_kwargs.get('one')
        two = view_kwargs.get('two')
        
        if one and two:
            try:
                program = Program.by_prog_inst(one, two)
            except Exception:
                pass
        
        # Fallback to request.program if set by other means
        if program is None:
            program = getattr(request, 'program', None)

        if program and program.is_online:
            tzname = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                try:
                    # UserPreferences is linked to ESPUser via 'preferences' related name.
                    tzname = request.user.preferences.timezone
                except Exception:
                    pass
            
            if not tzname:
                tzname = request.session.get('django_timezone')
            
            if tzname:
                try:
                    # Activate the timezone for the duration of the request
                    timezone.activate(pytz.timezone(tzname))
                except Exception:
                    timezone.deactivate()
            else:
                timezone.deactivate()
        else:
            # For in-person programs, use the default TIME_ZONE (deactivate active tz)
            timezone.deactivate()
            
        return None
