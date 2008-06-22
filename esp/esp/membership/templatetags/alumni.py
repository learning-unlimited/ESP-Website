from django import template
register = template.Library()
    
@register.filter
def alumni_reply_form(request, thread):
    from esp.membership.forms import AlumniMessageForm
    #   If the form is already there, don't mess with it.  
    #   Otherwise, come up with a blank one.
    if hasattr(thread, 'reply_form'):
        return thread.reply_form
    else:
        thread.reply_form = AlumniMessageForm(thread=thread, request=request)
        return thread.reply_form
