Equity Outreach Navigator
=========================

The Equity Outreach Navigator helps admins identify students who may need
additional support and send targeted outreach by email or SMS.

What it does
------------

This module provides:

* At-risk cohort cards with recipient counts.
* Recipient preview before sending.
* Campaign compose/send for email and SMS.
* Basic campaign history and recipient-level status logs.

Default cohorts
---------------

The initial release includes:

* Started profile but not confirmed
* Enrolled in classes but not confirmed
* Financial aid started but incomplete
* Potential transportation barrier
* Low class-hours or waitlisted

How to use
----------

1. Open ``Manage -> Equity Outreach Navigator`` for your program.
2. Review cohort counts and click **Preview**.
3. Click **Compose**, choose channel, write your message.
4. Send the campaign and review recipient log/status.

Operational notes
-----------------

* Email campaigns are queued through the existing message-request pipeline.
* SMS campaigns require Twilio settings to be configured.
* SMS respects user text-message preferences by default unless override is selected.
