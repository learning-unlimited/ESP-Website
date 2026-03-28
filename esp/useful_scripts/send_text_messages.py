import argparse
from twilio.rest import Client

parser = argparse.ArgumentParser(description="Send SMS messages")

parser.add_argument("account_sid", help="Twilio account SID to authenticate with")
parser.add_argument("auth_token", help="Twilio auth token corresponding to the account SID")
parser.add_argument("from_file", help="Path to file with sender phone numbers (one per line)")
parser.add_argument("to_file", help="Path to file with recipient phone numbers (one per line)")
parser.add_argument("message", help="Text message body to send to each recipient")

args = parser.parse_args()

account_sid = args.account_sid
auth_token = args.auth_token

with open(args.from_file) as from_f:
    ourNumbers = [x.strip() for x in from_f if x.strip()]

with open(args.to_file) as to_f:
    recipients = [x.strip() for x in to_f if x.strip()]

body = args.message
numberIndex = 0

for number in recipients:
    client = Client(account_sid, auth_token)
    print("Sending text message to " + number)
    client.messages.create(
        body=body,
        to=number,
        from_=ourNumbers[numberIndex]
    )
    numberIndex = (numberIndex + 1) % len(ourNumbers)
