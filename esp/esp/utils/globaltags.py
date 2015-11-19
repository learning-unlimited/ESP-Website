from django import template

# TODO: private API, please fix!
template.base.add_to_builtins('esp.web.templatetags.latex')
template.base.add_to_builtins('esp.web.templatetags.last')
