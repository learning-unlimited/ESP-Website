

from django import template
from esp.web.util.template import cache_inclusion_tag
from esp.miniblog.forms.form_comment import BlogCommentForm

register = template.Library()

@cache_inclusion_tag(register, 'inclusion/miniblog/single.html')
def render_blog(entry):
    return {'entry': entry}

@cache_inclusion_tag(register, 'inclusion/miniblog/single_comments.html')
def render_comments(entry, user, path, form):
    return {'entry': entry,
            'user': user,
            'path': path,
            'form': form}

