

from django import template
from esp.web.util.template import cache_inclusion_tag
from esp.miniblog.forms.form_comment import BlogCommentForm

register = template.Library()


def cache_key_func(entry):
    return 'BLOG_DISPLAY__%s' % entry.id

def comments_cache_key(entry, request=None, form=None):
    return None


@cache_inclusion_tag(register, 'inclusion/miniblog/single.html',cache_key_func=cache_key_func)
def render_blog(entry):

    return {'entry': entry}


@cache_inclusion_tag(register, 'inclusion/miniblog/single_comments.html',cache_key_func=comments_cache_key)
def render_comments(entry, request, form):
    return {'entry': entry,
            'request': request,
            'form': form}

