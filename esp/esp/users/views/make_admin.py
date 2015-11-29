from esp.users.models import admin_required
from esp.users.forms.make_admin import MakeAdminForm
from esp.utils.web import render_to_response

@admin_required
def make_admin(request):
    if request.method == 'POST':
        form = MakeAdminForm(request.POST)
        if form.is_valid():
            target_user = form.cleaned_data['target_user']
            target_user.makeAdmin()
            return render_to_response('users/make_admin_success.html', request, {'target_user': target_user})
    else:
        form = MakeAdminForm()

    return render_to_response('users/make_admin.html', request, {'form': form})
