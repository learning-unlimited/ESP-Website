ESP Email Setup
===============

This document describes how email, both incoming and outgoing, makes its way where it's going on the ESP website.  The code will serve as a more specific reference for the details, but this is an overview of the high-level setup.  Note: this document describes the setup on the LU production server; the parts of the setup outside the ESP-Website codebase may vary slightly on sites hosted elsewhere (in particular, esp.mit.edu).

.. contents:: :local:

Outgoing email
--------------

User-generated outgoing email originates in the comm panel.  The comm panel is outside the scope of this document, but after an admin writes an email and selects recipients, the website creates a single ``MessageRequest`` object with that data -- the email template, the list of students to which it will be sent, and some metadata like the sender.  (The ``MessageRequest`` model, and the others described below, are in ``esp/esp/dbmail/models.py``.)

Then, every 15 minutes at most (exact timing depends on the site), cron runs ``esp/dbmail_cron.py``.  This does two things.  First, it looks for unprocessed ``MessageRequest`` objects.  For each ``MessageRequest``, and for each user to which it is sent, the script creates a ``TextOfEmail`` object, which contains the email text exactly as it will be sent (as well as the subject, recipient address, and such).  It then marks the ``MessageRequest`` as processed.

After ``MessageRequest`` processing is complete, ``esp/dbmail_cron.py`` looks for unsent ``TextOfEmail`` objects.  For each one, it  sends the email, then marks the request as sent.  To send the email, we use the SendGrid API.

Incoming email
--------------

Incoming email is received by Exim, our Mail Transport Agent (MTA), via `SMTP <https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol>`_ and handled according to the settings in ``/etc/exim4``.  For mail at chapter-site domains, this mail is passed to the site's ``esp/mailgates/mailgate.py``.  This, in turn, consults the ``EmailList`` objects in the database (which on most sites are just the autocreated ones).

Each ``EmailList`` matches some regular expression of email addresses, and forwards the email to some list of users based on that.  (For example, class email lists match ``<emailcode>-students@``, and send to the class's students, teachers, and the admin archive list.)  Once we determine to whom to forward the email, we again use SendGrid to pass it on to the intended recipient(s). To protect personal information, we display the sender as their `username@site.learningu.org` alias. We will reject emails that are sent from an address not associated with a website account.


SendGrid Configuration
----------------------
Modern email providers require us to prove we are who we say we are by authenticating our domains (registered with Gandi and/or Amazon Web Services (AWS)) with our email provider(s), currently SendGrid. This process requires two steps: telling the email provider what domains we own and confirming that we own them by posting a unique record (that the email service gives us) to the domain registrar. See ``/lu/scripts/sendgrid_authentication.py`` to set everything up automatically with SendGrid and AWS.

