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

        # Try to get program from positional arguments (standard program views)
        if len(view_args) >= 3:
            one = view_args[1]
            two = view_args[2]
            try:
                program = Program.by_prog_inst(one, two)
            except Exception:
                pass

        if program is None:
            path_parts = [p for p in request.path.split('/') if p]
            if len(path_parts) >= 3 and path_parts[0] in ['learn', 'teach', 'onsite', 'manage', 'volunteer']:
                try:
                    program = Program.by_prog_inst(path_parts[1], path_parts[2])
                except Exception:
                    pass

        if program is None:
            program = getattr(request, 'program', None)

        tzname = request.COOKIES.get('user_timezone')
        if tzname:
            import urllib.parse
            tzname = urllib.parse.unquote(tzname)

        # For in-person programs, always use the default TIME_ZONE.
        if program and not program.is_online:
            tzname = None

        if not tzname and program and program.is_online:
            tzname = request.session.get('django_timezone')

        if tzname:
            try:
                # Activate the timezone for the duration of the request
                timezone.activate(pytz.timezone(tzname))
            except Exception:
                timezone.deactivate()
        else:
            timezone.deactivate()

        return None
