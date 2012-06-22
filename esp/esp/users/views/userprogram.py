from esp.users.models import ESPUser
from esp.program.models import RegistrationProfile

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

import simplejson as json

@login_required
def get_program(request):
    """ Get the user's profile
    """
    import ipdb
    if request.method == 'GET':
        profiles = RegistrationProfile.objects.filter(user__exact=request.user).select_related()

        # Group profiles by program
        programs = []
        results = []
        for profile in profiles:
            if profile.program:
                program = profile.program
                if not any(dict.get('title') == program.niceName() for dict in results):
                    program_dict = {}
                    program_dict['id'] = program.id
                    program_dict['title'] = program.niceName()
                    program_dict['baseUrl'] = program.getUrlBase()
                    results.append(program_dict)

        return HttpResponse(json.dumps(results))
