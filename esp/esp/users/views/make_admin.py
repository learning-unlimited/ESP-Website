from esp.users.models import admin_required
from esp.users.forms.make_admin import MakeAdminForm
from esp.utils.web import render_to_response

@admin_required
def make_admin(request):
    added_user = None
    if request.method == 'POST':
        form = MakeAdminForm(request.POST)
        if form.is_valid():
            target_user = form.cleaned_data['target_user']
            target_user.makeAdmin()
            added_user = target_user
            form = MakeAdminForm() # Reset form for the next user
    else:
        form = MakeAdminForm()

    return render_to_response('users/make_admin.html', request, {'form': form, 'added_user': added_user})
