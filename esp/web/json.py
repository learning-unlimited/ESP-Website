from django.http import HttpResponse
from django.utils import simplejson
from esp.users.models import UserBit
from django.db.models import Q
from esp.datatree.models import GetNode

class JsonResponse(HttpResponse):
    def __init__(self, obj):
        self.original_obj = obj
        HttpResponse.__init__(self, self.serialize())
#self["Content-Type"] = "application/json"
        self["Content-Type"] = "text/plain"

    def serialize(self):
        return(simplejson.dumps(self.original_obj))

def teacher_lookup(request, limit=10):
     # FIXME: REQUIRE PERMISSIONS!
    
    # Initialize anchors for identifying teachers
    q = GetNode( 'Q' )
    v = GetNode( 'V/Flags/Registration/Teacher' )
    
    # Select teachers
    queryset = UserBit.bits_get_users(q, v)

    # Search for teachers with names that start with search string
    startswith = request.GET['q']
    Q_firstname = Q(user__first_name__istartswith=startswith)
    Q_lastname = Q(user__last_name__istartswith=startswith)

    # Isolate user objects
    queryset = queryset.filter(Q_firstname | Q_lastname)[:(limit*10)]
    users = [ub.user for ub in queryset]
    user_dict = {}
    for user in users:
    	user_dict[user.id] = user
    users = user_dict.values()

    # Construct combo-box items
    obj_list = [[user.first_name + ' ' + user.last_name, user.id] for user in users]

    # Operation Complete!
    return JsonResponse(obj_list)
