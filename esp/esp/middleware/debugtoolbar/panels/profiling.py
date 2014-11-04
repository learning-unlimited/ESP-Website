from debug_toolbar.panels.profiling import ProfilingPanel

class ESPProfilingPanel(ProfilingPanel):
    """
    A subclass of ProfilingPanel that warns admins to disable it when not
    needed, since it incurs such a performance hit.

    Should be listed in the DISABLE_PANELS toolbar option so that it
    defaults to disabled.
    """

    @property
    def nav_subtitle(self):
        return 'Significantly slows site. Disable when not needed.'

