from esp.program.models import maybe_create_module_ext
from esp.program.modules.module_ext import StudentClassRegModuleInfo, ClassRegModuleInfo

# TODO(benkraft): There are actually a lot more modules that depend on these
# module extensions.  In practice it's probably fine because very few programs
# don't have the SCRM and TCRM, but maybe we should have other modules that
# also need these also autocreate them -- there's little harm in doing so.
# Ideally, we might even assert that only those modules access the settings,
# but doing that in practice might be hard.
maybe_create_module_ext('StudentClassRegModule', StudentClassRegModuleInfo)
maybe_create_module_ext('TeacherClassRegModule', ClassRegModuleInfo)
