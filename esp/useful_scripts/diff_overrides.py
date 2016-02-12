import sys
import difflib

#   for running from useful_scripts
sys.path.insert(0, '../')

from esp.utils.models import TemplateOverride

from django.template.loaders.filesystem import Loader
from django.conf import settings

def write_override_diff(diff_filename='template_overrides.diff'):

    #   Fetch latest version of each template override from database
    tos = TemplateOverride.objects.all().order_by('-version')
    newest_tos = {}
    for override in tos:
        if override.name not in newest_tos:
            newest_tos[override.name] = override
            print '%s (version %d)' % (override.name, override.version)

    #   Fetch the template file in the working copy
    orig_templates = {}
    template_loader = Loader()
    for key in newest_tos:
        try:
            orig_templates[key] = template_loader.load_template_source(key)
        except:
            print 'Could not load original template %s' % key

    print 'Got %d overrides and %d original versions' % (len(newest_tos.keys()), len(orig_templates.keys()))

    #   Compute diffs between original and overridden templates
    diff_filename = 'template_overrides.diff'
    file_out = open(diff_filename, 'w')
    for key in orig_templates:
        str1 = list([x.rstrip() for x in orig_templates[key][0].split('\n')])
        str2 = list([x.rstrip() for x in newest_tos[key].content.split('\n')])
        #   print '\n'.join(str1)
        #   print '\n'.join(str2)
        diff = difflib.unified_diff(str1, str2, key, key, lineterm='')
        for line in diff:
            file_out.write(line.encode('ascii', 'ignore') + '\n')
    file_out.close()

    print 'Wrote differences to %s' % diff_filename



if __name__ == '__main__':
    write_override_diff()


