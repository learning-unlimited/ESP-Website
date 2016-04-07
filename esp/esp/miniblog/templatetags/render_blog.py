

from django import template
from esp.utils.cache_inclusion_tag import cache_inclusion_tag

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

