from django import template
from django.shortcuts import render_to_response
from esp.utils.cache_inclusion_tag import cache_inclusion_tag
from esp.qsd.models import QuasiStaticData
from esp.tagdict.models import Tag

register = template.Library()

@cache_inclusion_tag(register,'inclusion/qsd/render_qsd.html')
def render_qsd(qsd):
    # check whether we should display the date and author footer (only affects non-administrator users)
    display_date_author_tag = Tag.getTag('qsd_display_date_author')
    display_date_author = 2 # display date and author

    if display_date_author_tag == 'Date':
        display_date_author = 1 # display date only
    elif display_date_author_tag == 'None':
        display_date_author = 0 # hide footer

    return {'qsdrec': qsd, 'display_date_author' : display_date_author}
render_qsd.cached_function.depend_on_row(QuasiStaticData, lambda qsd: {'qsd': qsd})
render_qsd.cached_function.depend_on_model(Tag)

@cache_inclusion_tag(register,'inclusion/qsd/render_qsd.html')
def render_inline_qsd(url):
    qsd_obj = QuasiStaticData.objects.get_by_url_else_init(url)
    return {'qsdrec': qsd_obj, 'inline': True}
render_inline_qsd.cached_function.depend_on_row(QuasiStaticData, lambda qsd: {'url':qsd.url})

@cache_inclusion_tag(register,'inclusion/qsd/render_qsd.html')
def render_inline_program_qsd(program, name):
    #unlike the above method, we don't know the url, just a program object
    #we could attempt to construct the url in the template
    #or just do this
    url = QuasiStaticData.prog_qsd_url(program, name)
    qsd_obj = QuasiStaticData.objects.get_by_url_else_init(url)
    return {'qsdrec': qsd_obj, 'inline': True}
def program_qsd_key_set(qsd):
    prog_and_name = QuasiStaticData.program_from_url(qsd.url)
    if prog_and_name is None:
        return None
    else:
        (program, name) = prog_and_name
        return {'program': program, 'name': name}
render_inline_program_qsd.cached_function.depend_on_row(QuasiStaticData, program_qsd_key_set)


class InlineQSDNode(template.Node):
    def __init__(self, nodelist, url, program_variable):
        self.nodelist = nodelist
        self.url = url
        self.program_variable = template.Variable(program_variable) if program_variable is not None else None

    def render(self, context):
        try:
            program = self.program_variable.resolve(context) if self.program_variable is not None else None
        except template.VariableDoesNotExist:
            program = None
        #   Accept literal string url argument if it is quoted; otherwise expect a template variable.
        #   template.Variable resolves string literals to themselves automatically
        url_resolved = template.Variable(self.url).resolve(context)
        if program is not None:
            url = QuasiStaticData.prog_qsd_url(program,url_resolved)
        else:
            url = url_resolved
        #probably should have an error message if variable was not None and prog was

        title = self.url
        if program is not None:
            title += ' - ' + unicode(program)

        qsd_obj = QuasiStaticData.objects.get_by_url_else_init(url, {'name': '', 'title': title, 'content': self.nodelist.render(context)})
        context.update({'qsdrec': qsd_obj, 'inline': True})
        # Note: this is django's render_to_response, not ours!
        return render_to_response("inclusion/qsd/render_qsd.html", context.flatten()).content

@register.tag
def inline_qsd_block(parser, token):
    tokens = token.split_contents()
    if len(tokens) == 2:
        iqb, url = tokens
    else:
        raise Exception("Wrong number of inputs for %s, 1 expected" % (tokens))

    nodelist = parser.parse(("end_inline_qsd_block",))
    parser.delete_first_token()

    return InlineQSDNode(nodelist, url, None)


@register.tag
def inline_program_qsd_block(parser, token):
    tokens = token.split_contents()
    if len(tokens) == 3:
        iqb, program, url = tokens
    else:
        raise Exception("Wrong number of inputs for %s, 2 expected" % (tokens))

    nodelist = parser.parse(("end_inline_program_qsd_block",))
    parser.delete_first_token()

    return InlineQSDNode(nodelist, url, program)

