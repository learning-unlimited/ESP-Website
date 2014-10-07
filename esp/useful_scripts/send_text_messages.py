import sys
from twilio.rest import TwilioRestClient

# TODO(jmoldow): Use Python built-in argparse module.
if len(sys.argv) < 6:
  print ("Usage: %s <account SID> <auth token> <file with line-separated phone numbers to send from> <file with line-separated phone numbers recipients> <message to send>" % sys.argv[0])
  exit(1)

account_sid = sys.argv[1]
auth_token = sys.argv[2]
ourNumbers = [x.strip() for x in open(sys.argv[3], "r").readlines() if x.strip()]
recipients = [x.strip() for x in open(sys.argv[4], "r").readlines() if x.strip()]
body = sys.argv[5]

numberIndex = 0

for number in recipients:
    client = TwilioRestClient(account_sid, auth_token)

    print "Sending text message to "+number
    client.sms.messages.create(body=body,
                               to=number,
                               from_=ourNumbers[numberIndex])
    numberIndex = (numberIndex + 1) % len(ourNumbers)
