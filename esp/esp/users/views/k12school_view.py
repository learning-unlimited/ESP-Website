from django.shortcuts import render, redirect
from django.contrib import messages
from esp.users.forms.k12school_form import K12SchoolForm
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def k12school_create(request):
    """
    A frontend view for admins to create new K12School objects.
    """
    if request.method == 'POST':
        form = K12SchoolForm(request.POST)
        if form.is_valid():
            new_school = form.save()
            messages.success(request, f'School "{new_school.name}" was successfully created!')
            return redirect('myesp-profile')
    else:
        form = K12SchoolForm()

    context = {'form': form}
    return render(request, 'users/k12school_form.html', context)
