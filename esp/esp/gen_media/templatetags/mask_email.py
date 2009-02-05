from esp.gen_media.emailimage import EmailImage
from django.template.defaultfilters import stringfilter
from django import template

register = template.Library()

@stringfilter
def mask_email(address):
    """
    Returns an image containing the email
    """
    image = EmailImage(address)
    return image.img
register.filter('mask_email', mask_email)

@stringfilter
def mask_email_concat(username, hostname):
    """
    Returns an image containing the email
    """
    return mask_email('%s@%s' % (username, hostname))
register.filter('mask_email_concat', mask_email_concat)

