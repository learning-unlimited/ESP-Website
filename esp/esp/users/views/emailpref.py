from esp.users.models import EmailPref
from esp.users.forms.user_reg import EmailPrefForm
from esp.web.util.main import render_to_response
from django.shortcuts import redirect


__all__ = ['emailpref']

#
# Email Preferences Page
#
# If called without arguments, show form to let user sign up for mailing list & SMS.
#
# If called with arguments, changes existing settings for an email address

def emailpref(request, success = None):

    if success:
        return render_to_response('users/emailpref_success.html',
                                  request,
                                  request.get_node('Q/Web/myesp'), {})

    if request.method == 'POST':
        form = EmailPrefForm(request.POST)

        if form.is_valid():
            ep, created = EmailPref.objects.get_or_create(email = form.cleaned_data['email'])

            ep.email_opt_in = True
	    ep.first_name = form.cleaned_data['first_name']
            ep.last_name = form.cleaned_data['last_name']
            ep.sms_number = form.cleaned_data['sms_number']
            ep.sms_opt_in = True if ep.sms_number else False
            ep.save()
            return redirect('/myesp/emailpref/success')
    else:
        form = EmailPrefForm()

    return render_to_response('users/emailpref.html',
                              request,
                              request.get_node('Q/Web/myesp'),
                              {'form': form})

