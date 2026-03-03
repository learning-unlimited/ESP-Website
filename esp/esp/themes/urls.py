
from esp.themes.views import editor, selector, configure, confirm_overwrite, landing, recompile, logos

from django.urls import path, re_path

urlpatterns = [
    re_path(r'^/?$', landing),
    path('/select', selector),
    path('/setup', configure),
    path('/confirm_overwrite', confirm_overwrite),
    path('/logos', logos),
    path('/customize', editor),
    path('/recompile', recompile),
]
