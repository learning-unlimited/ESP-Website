from django import template
from django.template import Context
from django.shortcuts import render_to_response
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

    

class InlineQSDNode(template.Node):
    def __init__(self, nodelist, input_anchor, qsd_name, user_variable):
        self.nodelist = nodelist
        self.qsd_name = qsd_name
        self.user_variable = template.Variable(user_variable)
        self.input_anchor = template.Variable(input_anchor)
        
    def render(self, context):
        try:
            user = self.user_variable.resolve(context)
        except template.VariableDoesNotExist:
            user = None

        anchor = self.input_anchor.resolve(context)

        qsd = self.qsd_name

        edit_bits = UserBit.UserHasPerms(user, anchor, DataTree.get_by_uri('V/Administer/Edit'))

        qsd_obj = anchor.quasistaticdata_set.filter(name=qsd).order_by('-id')[:1]
        if len(qsd_obj) == 0:
            new_qsd = QuasiStaticData()
            new_qsd.path = anchor
            new_qsd.name = qsd
            new_qsd.title = qsd
            new_qsd.content = self.nodelist.render(context)
            new_qsd.author = user
            new_qsd.save()
            qsd_obj = new_qsd
        else:
            qsd_obj = qsd_obj[0]

        return render_to_response("inclusion/qsd/render_qsd_inline.html", {'qsdrec': qsd_obj, 'edit_bits': edit_bits}, context_instance=context).content

        
@register.tag
def inline_qsd_block(parser, token):
    tokens = token.split_contents()
    if len(tokens) == 3:
        iqb, input_anchor, qsd_name = tokens
        user_variable = ""
    elif len(tokens) == 4:
        iqb, input_anchor, qsd_name, user_variable = tokens
    else:
        raise Exception("Wrong number of inputs for %s, either 2 or 3 expected" % (tokens))
    
    nodelist = parser.parse(("end_inline_qsd_block",))
    parser.delete_first_token()
    
    return InlineQSDNode(nodelist, input_anchor, qsd_name, user_variable)
    
