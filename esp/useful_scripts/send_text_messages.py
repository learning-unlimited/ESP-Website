from __future__ import absolute_import
from __future__ import print_function
import sys
import argparse
from twilio.rest import Client

parser = argparse.ArgumentParser(description="Send text messages using Twilio.")
parser.add_argument("account_sid", help="Twilio Account SID")
parser.add_argument("auth_token", help="Twilio Auth Token")
parser.add_argument("senders_file", help="File with line-separated phone numbers to send from")
parser.add_argument("recipients_file", help="File with line-separated phone numbers recipients")
parser.add_argument("message", help="Message to send")
args = parser.parse_args()

account_sid = args.account_sid
auth_token = args.auth_token
ourNumbers = [x.strip() for x in open(args.senders_file, "r").readlines() if x.strip()]
recipients = [x.strip() for x in open(args.recipients_file, "r").readlines() if x.strip()]
body = args.message

numberIndex = 0

for number in recipients:
    client = Client(account_sid, auth_token)

    print("Sending text message to "+number)
    client.messages.create(body=body,
                               to=number,
                               from_=ourNumbers[numberIndex])
    numberIndex = (numberIndex + 1) % len(ourNumbers)
