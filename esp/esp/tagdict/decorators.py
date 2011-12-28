from esp.tagdict.models import Tag

def require_tag(tag_name):
    def dec(func):
        if 'false' not in Tag.getTag(tag_name, default='false').lower():
            return func
        else:
            return (lambda *args, **kwargs: None)
    return dec
