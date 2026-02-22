from django.contrib.sites.models import Site
from django.conf import settings

from esp.program.models import Program
from esp.users.models import ESPUser

def media_url(request):
    return {'media_url': settings.MEDIA_URL}

def espuserified_request(request):
    return {'request': request, 'user': None, 'messages': None, 'perms': None}

def esp_user(request):
    return {'user': lambda: request.user}

def email_settings(request):
    context = {}
    context['DEFAULT_EMAIL_ADDRESSES'] = settings.DEFAULT_EMAIL_ADDRESSES
    context['EMAIL_HOST_SENDER'] = settings.EMAIL_HOST_SENDER
    context['settings'] = settings
    return context

def program(request):
    if getattr(request, "program", None):
        return {'program': request.program}
    elif getattr(request, "prog", None):
        return {'program': request.prog}
    else:
        path_parts = request.path.lstrip('/').split('/')
        if len(path_parts) > 3:
            program_url = '/'.join(path_parts[1:3])
            if Program.objects.filter(url=program_url).count() == 1:
                return {'program': Program.objects.get(url=program_url)}
    return {}

def schoolyear(request):
    program = None
    if getattr(request, "program", None):
        program = request.program
    elif getattr(request, "prog", None):
        program = request.prog
    else:
        path_parts = request.path.lstrip('/').split('/')
        if len(path_parts) > 3:
            program_url = '/'.join(path_parts[1:3])
            if Program.objects.filter(url=program_url).count() == 1:
                program = Program.objects.get(url=program_url)
    if program:
        return {'schoolyear': ESPUser.program_schoolyear(program)}
    else:
        return {'schoolyear': ESPUser.current_schoolyear()}

def index_backgrounds(request):
    #if request.path.strip() == '':
    return {'backgrounds': [settings.MEDIA_URL+"images/home/pagebkg1.jpg",
                            settings.MEDIA_URL+"images/home/pagebkg2.jpg",
                            settings.MEDIA_URL+"images/home/pagebkg3.jpg"]}
    return {}

def current_site(request):

    if hasattr(settings, 'SITE_INFO'):
        return {'current_site': Site(*settings.SITE_INFO) }

    return {'current_site': Site.objects.get_current()}

def preload_images(request):
    return {'preload_images': preload_images_data}

""" This list can be populated with images to be preloaded by the template.

    Example:
    preload_images_data = [
        settings.MEDIA_URL+'images/level3/nav/home_ro.gif',
        settings.MEDIA_URL+'images/level3/nav/discoveresp_ro.gif',
        (etc.)
        ]
"""

preload_images_data = [
]
