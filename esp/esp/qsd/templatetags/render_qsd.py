from django import template
from esp.datatree.models import DataTree
from esp.web.util.template import cache_inclusion_tag
from esp.qsd.models import QuasiStaticData
from urllib import quote

register = template.Library()

def cache_key(qsd):
    return 'QUASISTATICDATA__BLOCK__%s' % qsd.id


@cache_inclusion_tag(register,'inclusion/qsd/render_qsd.html', cache_key_func=cache_key)
def render_qsd(qsd):
    return {'qsdrec': qsd}

    
def cache_inline_key(input_anchor, qsd):
    return quote('QUASISTATICDATA__INLINE__BLOCK__%s__%s' % (input_anchor, qsd))

@cache_inclusion_tag(register,'inclusion/qsd/render_qsd_inline.html', cache_key_func=cache_inline_key)
def render_inline_qsd(input_anchor, qsd):
    
    if isinstance(input_anchor, basestring):
        try:
            anchor = DataTree.get_by_uri(input_anchor)
        except DatTree.NoSuchNodeException:
            return {}
                
    elif isinstance(input_anchor, DataTree):
        anchor = input_anchor
    else:
        return {}

    qsd_obj = anchor.quasistaticdata_set.filter(name=qsd).order_by('-id')
    if len(qsd_obj) == 0:
        return {}
    qsd_obj = qsd_obj[0]
    
    return {'qsdrec': qsd_obj}
