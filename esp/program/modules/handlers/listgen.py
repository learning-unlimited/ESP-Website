from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.program.manipulators import SATPrepInfoManipulator
from django import forms
from django.core.cache import cache
from esp.program.models import SATPrepRegInfo
from esp.users.models   import ESPUser
from django.db.models.query import Q, QNot
from django.template.defaultfilters import urlencode
from django.template import Context, Template
from esp.miniblog.models import Entry


class ListGenModule(ProgramModuleObj):
    """ This module is useful to generate lists for the program directors. """

    @needs_admin
    def selectList(self, request, tl, one, two, module, extra, prog):
        """ Select the type of list that is requested. """
        from esp.users.views     import get_user_list
        from esp.users.models    import User
        from esp.users.models import PersistentQueryFilter

        if not request.GET.has_key('filterid'):
            filterObj, found = get_user_list(request, self.program.getLists(True))
        else:
            filterid  = request.GET['filterid']
            filterObj = PersistentQueryFilter.getFilterFromID(filterid, User)
            found     = True
        if not found:
            return filterObj

        if not request.GET.has_key('type'):
            return render_to_response(self.baseDir()+'options.html', request, (prog, tl), {'filterid': filterObj.id})

        strtype = request.GET['type']

        users = [ ESPUser(user) for user in ESPUser.objects.filter(filterObj.get_Q()).distinct()]

        users.sort()
        
        return render_to_response(self.baseDir()+('list_%s.html'%strtype), request, (prog, tl), {'users': users})
                                                                                                 
