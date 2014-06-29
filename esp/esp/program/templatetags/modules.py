from django import template

register = template.Library()

@register.filter
def hasModule(program, module):
    return program.hasModule(module)
