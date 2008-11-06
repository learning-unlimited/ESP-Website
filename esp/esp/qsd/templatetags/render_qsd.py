import md5
from django import template
from esp.datatree.models import *
from esp.users.models import UserBit
from esp.web.util.template import cache_inclusion_tag, DISABLED
from esp.qsd.models import QuasiStaticData
from esp.qsd.models import qsd_cache_key
from urllib import quote

from esp.utils.file_cache import FileCache

register = template.Library()

render_qsd_cache = FileCache(4, 'render_qsd')

def cache_key(qsd, user=None):
    return qsd_cache_key(qsd.path, qsd.name, user,)


@cache_inclusion_tag(register,'inclusion/qsd/render_qsd.html', cache_key_func=cache_key, cache_obj=render_qsd_cache, cache_time=300)
def render_qsd(qsd, user=None):
    edit_bits = False
    if user:
        edit_bits = UserBit.UserHasPerms(user, qsd.path, DataTree.get_by_uri('V/Administer/Edit'))
    return {'qsdrec': qsd, 'edit_bits': edit_bits}

def cache_inline_key(input_anchor, qsd, user=None):
    if user:
        return quote('QUASISTATICDATA__INLINE__BLOCK__%s__%s__%s' % (input_anchor, qsd, user.id))
    else:
        return quote('QUASISTATICDATA__INLINE__BLOCK__%s__%s' % (input_anchor, qsd))

@cache_inclusion_tag(register,'inclusion/qsd/render_qsd_inline.html', cache_key_func=cache_inline_key, cache_obj=DISABLED)
def render_inline_qsd(input_anchor, qsd, user=None):
    if isinstance(input_anchor, basestring):
        try:
            anchor = DataTree.get_by_uri(input_anchor)
        except DataTree.NoSuchNodeException:
            return {}
                
    elif isinstance(input_anchor, DataTree):
        anchor = input_anchor
    else:
        return {}

    edit_bits = False
    if user:
        edit_bits = UserBit.UserHasPerms(user, anchor, DataTree.get_by_uri('V/Administer/Edit'))
    qsd_obj = anchor.quasistaticdata_set.filter(name=qsd).order_by('-id')
    if len(qsd_obj) == 0:
        return {'edit_bits': edit_bits, 'qsdname': qsd, 'anchor_id': anchor.id}
    qsd_obj = qsd_obj[0]
    
    return {'qsdrec': qsd_obj, 'edit_bits': edit_bits}
