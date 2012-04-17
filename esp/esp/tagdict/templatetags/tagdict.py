from django import template
from django.template.base import Node
from esp.tagdict.models import Tag
from esp.program.models import ClassSubject

register = template.Library()

class GetProgramTagNode(Node):
    """ Gives access to the getProgramTag function """

    def __init__(self, key, program, default):
        self.key = key
        self.program = program
        self.default = default

    @classmethod
    def handle_token(cls, parser, token):
        """ Class method to handle the tokens received """
        tokens = token.contents.split()
        if len(tokens) < 2:
            raise template.TemplateSyntaxError("At least 2 arguments required")
        key = parser.compile_filter(tokens[1])
        program = None
        default = None
        if len(tokens) > 2:
            program = parser.compile_filter(tokens[2])
        if len(tokens) > 3:
            default = parser.compile_filter(tokens[3])

        return cls(key, program, default)
      

    def render(self, context):
        key = self.key.resolve(context)
        if self.program:
            program = self.program.resolve(context)
        else:
            program = None
        if self.default:
            default = self.default.resolve(context)
        else:
            default = None
        return str(Tag.getProgramTag(key, program, default))


def doGetProgramTag(parser, token):
    return GetProgramTagNode.handle_token(parser, token)

register.tag('getProgramTag', doGetProgramTag)
