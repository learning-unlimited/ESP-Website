import sys
from twilio.rest import TwilioRestClient
account_sid = "AC0f79038e0b69e5ac71eb4854ac8f6d02"
auth_token = "f3900990f80e47c9b75eafa6cfc37cbb"

ourNumbers = ["+1 617-606-4889"]
numberIndex = 0
if len(sys.argv) < 2:
  sys.stderr.write("Usage: %s <file with line-separated phone numbers>\n" % sys.argv[0])
  exit(1)

numberFile = open(sys.argv[1], "r")

for number in numberFile.readlines():
    client = TwilioRestClient(account_sid, auth_token)

    print "Sending text message to "+number
    client.sms.messages.create(body=body,
                               to=number,
                               from_=ourNumbers[numberIndex])
    numberIndex = (numberIndex + 1) % len(ourNumbers)


