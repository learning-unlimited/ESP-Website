"""
Makes a bunch of shortlinks.

Takes in:
-A spreadsheet stored in 'redirects_spreadsheet.csv'
--The spreadsheet has fields shortlink,destination,src
Result:
-A shortlink is created ([shortlink] -> [destination]?src=[src]) for each row.
"""

from script_setup import *
import csv

def encode_get(gets):
    out = []
    first = True
    for key, val in gets.items():
        if not first:
            out.append("&")
        first = False
        out.append(key)
        out.append("=")
        out.append(val)
    return "".join(out)

def create_shortlink(short_link, long_link, get={}, overwrite=False):
    site = Site.objects.get(domain='esp.mit.edu')
    dest = long_link + "?" + encode_get(get)
    r = Redirect.objects.filter(site=site, old_path=short_link)
    if r.exists():
        assert overwrite, "Overwrites not enabled, run again with overwrite=True"
        r.update(new_path=dest)
    else:
        Redirect.objects.create(site=site, old_path=short_link, new_path=dest)

if __name__ == '__main__':
    with open("redirects_spreadsheet.csv", "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            args = row["shortlink"], row["destination"], {"src": row["src"]}, True
            print(args)
            create_shortlink(*args)
