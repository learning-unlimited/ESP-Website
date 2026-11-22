from __future__ import absolute_import
import itertools
import json

from django import template

from esp.utils.models import Printer

register = template.Library()


@register.simple_tag
def print_locations():
    """The locations a document can be printed to, Default first."""
    return list(Printer.objects.active().order_by('-is_default', 'name'))


#   The settings fields the print panel offers (its fields' names are the
#   keys esp.program.controllers.printing.clean_settings takes)
PANEL_SETTINGS = (('sides', 'Sides'), ('color_mode', 'Color mode'), ('quality', 'Quality'),
                  ('media', 'Paper'), ('scaling', 'Scaling'))
_panel_ids = itertools.count(1)


@register.inclusion_tag('program/modules/dayof/print_panel.html')
def print_panel(copies=True, legend='Printer settings', button='Print', submit=True, settings=True,
                settings_open=False, watch='', **defaults):
    """ The print panel, for a form (or a script) that prints a document:
    where to print (remembered in the browser, the same choice everywhere
    on the site), that printer's settings, and, with copies, how many.
    Other arguments are settings to start from for this document (e.g.
    sides="one-sided"), where the printer can do them. The view reads
    the fields with printing.print_panel_values. Its Print button (labeled
    button) submits the form it's in (with action=print), or, with
    submit=False, is for a script to handle (see print_panel.js); button=''
    leaves it out (for a page with its own print buttons). settings=False
    leaves out the printer settings (just where to print); otherwise they're
    in a section collapsed unless settings_open. watch: ids of jobs just
    sent (e.g. "4,5", from the page's ?jobs=), whose progress the panel
    shows as it happens (as it does for jobs a script hands to
    espPrintPanel.watch). """
    from esp.program.controllers import printing
    locations = printing.print_panel_locations()
    data = {'locations': locations, 'defaults': defaults or {},
            'watch': [int(i) for i in str(watch or '').split(',') if i.strip().isdigit()],
            'status_url': '/manage/printers/printers_job_status'}
    return {
        'panel_id': 'print-panel-%d' % next(_panel_ids),
        'locations': locations,
        'copies': copies,
        'max_copies': printing.MAX_COPIES,
        'setting_fields': PANEL_SETTINGS,
        'legend': legend,
        'button': button,
        'submit': submit,
        'settings': settings,
        'settings_open': settings_open,
        'data_json': json.dumps(data).replace('<', '\\u003c'),
    }
