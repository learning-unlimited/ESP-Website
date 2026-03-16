import logging
import os
import subprocess
import tempfile

from django.conf import settings

from esp.tests.util import CacheFlushTestCase as TestCase

logger = logging.getLogger(__name__)


class JavascriptSyntaxTest(TestCase):
    def runTest(self, display=False):
        if hasattr(settings, "CLOSURE_COMPILER_PATH"):
            closure_path = settings.CLOSURE_COMPILER_PATH.rstrip("/") + "/"
        else:
            closure_path = ""

        if not os.path.exists("%scompiler.jar" % closure_path):
            if display:
                logger.info(
                    'Closure compiler not found. Checked CLOSURE_COMPILER_PATH ="%s"',
                    closure_path,
                )
            return

        closure_output_code = tempfile.gettempdir() + "/closure_output.js"
        closure_output_file = tempfile.gettempdir() + "closure.out"

        base_path = settings.MEDIA_ROOT + "scripts/"
        exclude_names = ["yui", "extjs", "jquery", "showdown"]

        file_list = []
        for dirpath, _dirnames, filenames in os.walk(base_path):
            if any(name in dirpath for name in exclude_names):
                continue

            if display:
                logger.info("Entering directory %s", dirpath)

            for file in filenames:
                if not file.endswith(".js"):
                    continue
                if any(name in file for name in exclude_names):
                    continue
                file_list.append("%s/%s" % (dirpath, file))

        cmd = ["java", "-jar", "%s/compiler.jar" % closure_path]
        for file in file_list:
            cmd.extend(["--js", file])
        cmd.extend(["--js_output_file", closure_output_code])

        with open(closure_output_file, "w") as err_file:
            subprocess.run(cmd, stderr=err_file, stdout=subprocess.DEVNULL, check=True)

        with open(closure_output_code) as checkfile:
            results = [line.rstrip("\n") for line in checkfile.readlines() if len(line.strip()) > 0]

        if len(results) > 0:
            closure_result = results[-1].split(",")
            num_errors = int(closure_result[0].split()[0])
            num_warnings = int(closure_result[1].split()[0])

            logger.info(
                "-- Displaying Closure results: %d Javascript syntax errors, %d warnings",
                num_errors,
                num_warnings,
            )
            for line in results:
                logger.info(line)

            self.assertEqual(num_errors, 0, "Closure compiler detected Javascript syntax errors")
