from esp.datatree.models import GetNode
from esp.users.models import ESPUser, UserBit
from esp.program.models import RegistrationProfile, Program

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

import simplejson as json

def json_program(list):
    results = []
    for program in list:
        if program and not any(dict.get('id') == program.id for dict in results):
            program_dict = {}
            program_dict['id'] = program.id
            program_dict['title'] = program.niceName()
            program_dict['baseUrl'] = program.getUrlBase()
            results.append(program_dict)
    return json.dumps(sorted(results, key=lambda program: program['title']))

@login_required
def get_program(request):
    """ Get the list of programs that the user belongs to
    """
    if request.method == 'GET':
        user = ESPUser(request.user)
        if user.isOnsite():
            verb = GetNode('V/Registration/OnSite')

            programs = UserBit.find_by_anchor_perms(Program, user=user, verb=verb)
        elif user.isStudent():
            profiles = RegistrationProfile.objects.filter(user__exact=request.user).select_related()

            programs = [profile.program for profile in profiles]
        return HttpResponse(json_program(programs))
