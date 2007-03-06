from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.program.models  import Class, Program
from esp.web.util        import render_to_response
from esp.datatree.models import DataTree
from django.contrib.auth.decorators import login_required


class ClassRoomModule(ProgramModuleObj):
    """ While at some point this will be deprecated, for now this is how you add a room to your program.
    At some point, rooms will have useful things tied to them magically."""
    @needs_admin
    def managerooms(self, request, tl, one, two, module, extra, prog):

        return render_to_response(self.baseDir()+'managerooms.html', request, (prog, tl), {})
    


    @needs_admin
    def addroom(self, request, tl, one, two, module, extra, prog):
        shortname = request.POST['shortname']
        name      = request.POST['name']
        self.program.addClassRoom(name, shortname)

        return self.goToCore(tl)
    
    @needs_admin
    def assignroom(self, request, tl, one, two, module, extra, prog):
        classes = Class.objects.filter(id = extra)
        if len(classes) != 1 or not self.user.canEdit(classes[0]):
            return render_to_response(self.baseDir()+'cannoteditclass.html', request, (prog, tl),{})
        cls = classes[0]
        trees = DataTree.objects.filter(id = request.POST['roomid'])
        
        cls.assignClassRoom(trees[0])
        
        return self.goToCore(tl)
