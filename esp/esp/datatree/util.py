

def tree_filter(kwargs):
    """
    Takes any input to filter and changes the
    kwargs to work with __above and __below for a tree.
    """
    new_kwargs = {}

    for key, node in kwargs.iteritems():
        action = key.strip()[-7:]
        if action != '__below' and action != '__above':
            new_kwargs[key] = node
            continue

        if not hasattr(node, 'rangeend') or not hasattr(node, 'rangestart'):
            raise ValueError('__above or __below requires a datatree node, recieved "%s"' % node)
        
        if action == '__below':
            new_kwargs[key[:-5]+'rangestart__gte'] = node.rangestart
            new_kwargs[key[:-5]+'rangeend__lte']   = node.rangeend
        else:
            new_kwargs[key[:-5]+'rangestart__lte'] = node.rangestart
            new_kwargs[key[:-5]+'rangeend__gte']   = node.rangeend

    return new_kwargs

def tree_filter_kwargs(**kwargs):
    return tree_filter(kwargs)
