from django.template import Library
from django.utils.safestring import mark_safe

register = Library()

def userlist(var, delimiter):
	atag = lambda x:'<a href="{0}">{1}</a>'.format(x.get_absolute_url(),unicode(x))
	userlist_html = '{0} '.format(delimiter).join([atag(i) for i in var])
	return mark_safe(userlist_html)

register.filter(userlist)