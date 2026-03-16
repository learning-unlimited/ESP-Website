from django.conf import settings
from django.core.management.base import BaseCommand

import logging
logger = logging.getLogger(__name__)
import os

class Command(BaseCommand):
    """
    Clean out *.pyc files that contain stale code.

    In practice, the only files that cause problems are orphaned *.pyc's where
    the corresponding *.py file has been deleted (git leaves the *.pyc in
    place). Other than this, *.pyc files cannot be stale because git updates the
    lastmod time when changing a file, so a freshly checked out *.py file will
    always be newer than its *.pyc, triggering a recompile. This is an
    optimization over Django's original clean_pyc, which deletes all *pyc's in
    the source tree.
    """
    def handle(self, *args, **options):
        root = os.path.dirname(os.path.abspath(settings.BASE_DIR))
        ret = os.system("find " + root + """ -name '*.pyc' -exec bash -c 'test ! -f "${1%c}"' -- {} \; -delete""")
        if ret:
            logger.info("Aborting with return code", ret)
            exit(ret)
