from django import template
from esp.web.util.template import cache_inclusion_tag

register = template.Library()

def cache_key(qsd):
    return 'QUASISTATICDATA__BLOCK__%s' % qsd.id


@cache_inclusion_tag(register,'inclusion/qsd/render_qsd.html', cache_key_func=cache_key)
def render_qsd(qsd):
    return {'qsdrec': qsd}
