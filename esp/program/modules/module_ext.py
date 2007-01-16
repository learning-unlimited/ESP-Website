from django.db import models
from esp.program.modules.base import ProgramModuleObj

class ClassRegModuleInfo(models.Model):
    module       = models.ForeignKey(ProgramModuleObj)
    allow_coteach        = models.BooleanField()
    display_times        = models.BooleanField()
    times_selectmultiple = models.BooleanField()

    class Admin:
        pass
    


class CreditCardModuleInfo(models.Model):
    module = models.ForeignKey(ProgramModuleObj)
    base_cost        = models.IntegerField()

    class Admin:
        pass
    
