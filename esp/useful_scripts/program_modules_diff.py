"""Script to check which programs have modified their ProgramModules."""

from script_setup import *
from esp.program.models import ProgramModule

print
for module in ProgramModule.objects.all():
    try:
        default_propss = module.getPythonClass().module_properties_autopopulated()
    except ProgramModule.CannotGetClassException:
        pass
    else:
        for default_props in default_propss:
            if default_props['module_type'] != module.module_type or default_props['handler'] == 'OnSiteClassList':
                continue
            if 'required' not in default_props:
                default_props['required'] = False
            for key in ['admin_title', 'link_title', 'seq', 'required']:
                if getattr(module, key) != default_props.get(key):
                    print "\t%s.%s" % (module.handler, key)
                    print "\t\tdefault %s" % default_props.get(key)
                    print "\t\tactual  %s" % getattr(module, key)
