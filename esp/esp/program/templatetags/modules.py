from django import template

register = template.Library()

@register.filter
def hasModule(program, module):
    """True if the program has the given module.  False otherwise, or if the
    program is None."""
    if program is None:
        return False
    else:
        return program.hasModule(module)
