from debug_toolbar.panels.profiling import ProfilingPanel

class ESPProfilingPanel(ProfilingPanel):
    """
    A subclass of ProfilingPanel that defaults to disabled rather than enabled,
    since it incurs such a performance hit. This lets us have the panel always
    display and makes it easier to enable when it is needed.
    """

    @property
    def enabled(self):
        return self.toolbar.request.COOKIES.get('djdt' + self.panel_id, 'off') == 'on'

    @property
    def nav_subtitle(self):
        return 'Significantly slows site. Disable when not needed.'

