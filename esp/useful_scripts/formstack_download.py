#
# ESP-Formstack Data Downloader
# formstack_download.py
#
# Downloads a large, encrypted Formstack form in smaller batches (as the
# online dowlnoad times out)
#
# Requires a safe directory in which to write data (the same one as the
# script is running from) and a certificate bundle downloaded to the same
# directory and named cacert.pem - see http://curl.haxx.se/ca/cacert.pem
#

import json
import pycurl
import sys

SUBMISSIONS_PER_PAGE = 100
#  when enumerating form submissions, the maximum number of metadatas
#  (submission id, timestamp, etc) to download in one batch; going over
#  this limit will typically cause Formstack to revert to 25/page or so.

API_BASE = "https://www.formstack.com/api/v2/"
#   trailing slash, please

BATCH_SIZE = 500
#  number of submissions to include in one export job (i.e. RTF or CSV)


# Collect Formstack Connection Information
print "Formstack Data Downloader"
print "-------------------------"
print ""

oauth_token = raw_input("Access Token (see bit.ly/uoT3B2): ")
form_id = raw_input("Form ID (from URL of edit page): ")
encryption_password = raw_input("Encryption password: ")
output_format = raw_input("Output format (csv/RTF): ")

if output_format.lower() == "csv":
    output_format = "csv"
    print "  Selected CSV"
else:
    output_format = "rtf"
    print "  Selected RTF"


# Download List of IDs
#   pycurl code thanks to [bit.ly/StT2y8]
ids = set()

class Response(object):
    """ utility class to collect the response """
    def __init__(self):
        self.chunks = []
    def callback(self, chunk):
        self.chunks.append(chunk)
    def content(self):
        return ''.join(self.chunks)

n = 1
limit = 1
#  num pages, will be update later with the real value as reported by Formstack

while n <= limit:
    url = API_BASE + "form/" + form_id + "/submission" + \
          "?page=" + str(n) + \
          "&per_page=100" + \
          "&sort=ASC" + \
          "&oauth_token=" + oauth_token + \
          "&encryption_password=" + encryption_password

    res = Response()
    curl = pycurl.Curl()
    curl.setopt(curl.URL, url)
    curl.setopt(curl.WRITEFUNCTION, res.callback)
    curl.setopt(curl.CAINFO, "cacert.pem")
    curl.perform()

    http_code = curl.getinfo(curl.HTTP_CODE)
    result = res.content()

    if http_code != 200:
        print "HTTP ERROR " + str(http_code)
        print "  on iteration " + str(n)
        print result

    form_data = json.loads(result)

    for submission in form_data['submissions']:
        ids.add(submission['id'])

    if n == 1:
        limit = form_data['pages']
        #  true number of pages of data

        print ""
        sys.stdout.write("[ " + str(limit) + " ] ")

    sys.stdout.write(" " + str(n))
    n += 1
    #  now to the next page


# Create Download Helper
#  divide up into batches of BATCH_SIZE, prepare POST requests
f = open('formstack_download.html', 'w')

batch = 1
while len(ids) > 0:
    f.write("""
<form action="https://www.formstack.com/admin/submission/export/406852" method="post">
  <input type="hidden" name="exportWhich" value="selected">
  <input type="hidden" name="exportType" value=\"""")
    f.write(output_format)
    f.write("""\">
  <input type="hidden" name="exportIDs" value=\"""")

    n = 1
    while n <= BATCH_SIZE and len(ids) > 0:
        if n > 1:
            f.write(",")
        f.write(ids.pop())
        n += 1
        # end mini loop

    f.write("""\">
  <input type="hidden" name="dataview" value="1">
  <input type="submit" value="Download Batch """)
    f.write(str(batch))
    f.write("""\">
</form>
""")

    batch += 1
    #  now to the next batch

f.close()

print ""
print ""
print "Helper File writen to formstack_download.html"
print "You must be logged in to Formstack in order to use it"
