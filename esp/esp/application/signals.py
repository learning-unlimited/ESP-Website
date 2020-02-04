from esp.program.models import maybe_create_module_ext
from esp.application.models import FormstackAppSettings

maybe_create_module_ext('FormstackAppModule', FormstackAppSettings)
