from django.contrib.auth.models import Group
from django.db import transaction
from django.db.utils import IntegrityError

from esp.users.models import admin_required
from esp.users.forms.make_admin import MakeAdminForm
from esp.web.util.main import render_to_response
from esp.users.models import UserBit
from esp.datatree.models import *

@admin_required
def make_admin(request):
    if request.method == 'POST':
        form = MakeAdminForm(request.POST)
        if form.is_valid():
            target_user = form.cleaned_data['target_user']
            make_user_admin(target_user)
            return render_to_response('users/make_admin_success.html', request, request.get_node('Q/Programs/'), {'target_user': target_user})
    else:
        form = MakeAdminForm()

    return render_to_response('users/make_admin.html', request, request.get_node('Q/Programs/'), {'form': form})

def make_user_admin(target_user):
    # Set the flags for Django's auth system
    setattr(target_user, 'is_staff', True)
    setattr(target_user, 'is_superuser', True)

    # Set the userbits
    target_user.userbit_set.add(UserBit(verb = GetNode('V/Administer'), qsc = GetNode('Q')))
    target_user.makeRole("Administrator")

    target_user.save()
