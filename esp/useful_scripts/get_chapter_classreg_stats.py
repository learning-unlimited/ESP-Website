"""Gets class registration data for all programs ever, by chapter.

Best run with run_queries.sh.
"""
import csv
import logging

from script_setup import *

from django.conf import settings

from esp.program.models import Program

def all_data():
    group_name = (Tag.getTag('full_group_name') or
                  '%s %s' % (settings.INSTITUTION_NAME,
                             settings.ORGANIZATION_SHORT_NAME))
    for program in Program.objects.order_by('-id'):
        numbers = [group_name, program.url]
        try:
            numbers.append(program.students()['enrolled'].count())
            numbers.append(program.students()['attended'].count())
        except:
            logging.error("Couldn't get number of students for %s" %
                          program.url)
        finally:
            yield numbers

def main(outfile):
    with open(outfile, 'a') as f:
        w = csv.writer(f)
        w.writerows(all_data())

if __name__ == '__main__':
    main('/home/benkraft/chapter_classreg_stats.csv')
