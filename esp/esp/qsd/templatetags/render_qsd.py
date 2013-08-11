from django import template
from django.shortcuts import render_to_response
from django.core.cache import cache
from esp.users.models import Permission
from esp.web.util.template import cache_inclusion_tag, DISABLED
from esp.qsd.models import QuasiStaticData
from esp.qsd.models import qsd_cache_key
from urllib import quote

register = template.Library()

@cache_inclusion_tag(register,'inclusion/qsd/render_qsd.html')
def render_qsd(qsd):
    return {'qsdrec': qsd}
render_qsd.cached_function.depend_on_row(QuasiStaticData, lambda qsd: {'qsd': qsd})

@cache_inclusion_tag(register,'inclusion/qsd/render_qsd_inline.html')
def render_inline_qsd(url):
    try:
        qsd_obj = QuasiStaticData.objects.get_by_url(url)
    except QuasiStaticData.DoesNotExist:
        return {'url':url}
    
    return {'qsdrec': qsd_obj}
render_inline_qsd.cached_function.depend_on_row(QuasiStaticData, lambda qsd: {'url':qsd.url})

@cache_inclusion_tag(register,'inclusion/qsd/render_qsd_inline.html')
def render_inline_program_qsd(program, name):
    #unlike the above method, we don't know the url, just a program object
    #we could attempt to construct the url in the template
    #or just do this
    url = QuasiStaticData.prog_qsd_url(program, name)
    try:
        qsd_obj = QuasiStaticData.objects.get_by_url(url)
    except QuasiStaticData.DoesNotExist:
        return {'url':url}
    
    return {'qsdrec': qsd_obj}
render_inline_qsd.cached_function.depend_on_row(QuasiStaticData, lambda qsd: {'url':qsd.url})
    

class InlineQSDNode(template.Node):
    def __init__(self, nodelist, url, user_variable, program_variable):
        self.nodelist = nodelist
        self.url = url
        self.user_variable = template.Variable(user_variable) if user_variable is not None else None
        self.program_variable = template.Variable(program_variable) if program_variable is not None else None
        
    def render(self, context):
        try:
            user = self.user_variable.resolve(context) if self.user_variable is not None else None
        except template.VariableDoesNotExist:
            user = None
        try:
            program = self.program_variable.resolve(context) if self.program_variable is not None else None
        except template.VariableDoesNotExist:
            program = None
        if program is not None:
            url = QuasiStaticData.prog_qsd_url(program,self.url)
        else:
            url = self.url
        #probably should have an error message if variable was not None and prog was

        edit_bits = Permission.user_can_edit_qsd(user, url)

        qsd_obj = QuasiStaticData.objects.get_by_url(url)
        if qsd_obj == None:
            new_qsd = QuasiStaticData()
            new_qsd.url = url
            new_qsd.title = url
            new_qsd.content = self.nodelist.render(context)
            
            if getattr(user, 'id', False):
                new_qsd.author = user
                new_qsd.save()

            qsd_obj = new_qsd

        return render_to_response("inclusion/qsd/render_qsd_inline.html", {'qsdrec': qsd_obj, 'edit_bits': edit_bits}, context_instance=context).content

@register.tag
def inline_qsd_block(parser, token):
    tokens = token.split_contents()
    if len(tokens) == 2:
        iqb, url = tokens
        user_variable = None
    elif len(tokens) == 3:
        iqb, url, user_variable = tokens
    else:
        raise Exception("Wrong number of inputs for %s, either 1 or 2 expected" % (tokens))
    
    nodelist = parser.parse(("end_inline_qsd_block",))
    parser.delete_first_token()
    
    return InlineQSDNode(nodelist, url, user_variable, None)


@register.tag
def inline_program_qsd_block(parser, token):
    tokens = token.split_contents()
    if len(tokens) == 3:
        iqb, program, url = tokens
        user_variable = None
    elif len(tokens) == 4:
        iqb, program, url, user_variable = tokens
    else:
        raise Exception("Wrong number of inputs for %s, either 1 or 2 expected" % (tokens))
    
    nodelist = parser.parse(("end_inline_program_qsd_block",))
    parser.delete_first_token()
    
    return InlineQSDNode(nodelist, url, user_variable, program)


class QSDStringNode(template.Node):
    def __init__(self, input_url):
        self.url = url
      
    def render(self, context):
        try:
            qsd_obj = QuasiStaticData.objects.get_by_url(self.url)
            result = qsd_obj.content
        except AttributeError:
            result = "QSD Does Not Exist"        
        return result

@register.tag
def qsd_string(parser, token):
    tag, url = token.split_contents()
    return QSDStringNode(url)
    
