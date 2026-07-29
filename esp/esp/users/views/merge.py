#from django.contrib.auth.decorators import login_required
from __future__ import absolute_import
from esp.users.models import admin_required
from esp.users.controllers.merge import merge_users
from esp.users.forms.merge import UserMergeForm
from esp.utils.web import render_to_response

@admin_required
def merge_accounts(request):
    if request.method == 'POST':
        form = UserMergeForm(request.POST)
        if form.is_valid():
            new_user, old_user, forward, deactivate = form.cleaned_data['absorber'], form.cleaned_data['absorbee'], form.cleaned_data['forward'], form.cleaned_data['deactivate']
            merge_users(new_user, old_user, forward=forward, deactivate = deactivate)
            return render_to_response('users/merge_success.html', request, {'new_user': new_user, 'old_user': old_user})
    else:
        form = UserMergeForm()

    return render_to_response('users/merge_accounts.html', request, {'form': form})
