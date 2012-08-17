from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson

from esp.datatree.models import DataTree

def ajax_children(request):
    """ Return a JSON object with information about the DataTrees that are children of a given DataTree. """
    
    try:
        limit = int(request.GET.get('limit',0))
        tree_id = int(request.GET.get('id', '0'))
        node = DataTree.objects.get(id=tree_id)
    except (KeyError, ValueError, DataTree.DoesNotExist):
        # bad request
        response = HttpResponse('Malformed Input')
        response.status_code = 400
        return response

    if limit > 0:
        output = list(node.descendants().exclude(id=tree_id)[:limit])
        direct_children = list(node.children().exclude(id=tree_id)[:limit])
    else:
        output = list(node.descendants().exclude(id=tree_id))
        direct_children = list(node.children().exclude(id=tree_id))
    output.sort(key=lambda x: x.rangestart)
    direct_children = [c.id for c in direct_children]
    items = {}
    for item in output:
        children = [c.id for c in item.children()]
        items[item.id] = {
            'id': str(item.id),
            'name': item.name,
            'data': item.name, # jstree expects the name to be called "data"
            'type': 'DataTree',
            'parent_id': str(item.parent_id),
            'friendly_name': item.friendly_name.replace("'",""),
            'children': children
        }
    
    output2 = {'items': items, 'direct_children': direct_children}
    content = simplejson.dumps(output2)

    return HttpResponse(content, mimetype = 'javascript/javascript')
