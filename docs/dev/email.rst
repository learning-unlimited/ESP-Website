ESP Email Setup
===============

This document describes how email, both incoming and outgoing, makes its way where it's going on the ESP website.  The code will serve as a more specific reference for the details, but this is an overview of the high-level setup.  Note: this document describes the setup on diogenes; the parts of the setup outside the ESP-Website codebase may vary slightly on sites hosted elsewhere (i.e. esp.mit.edu).

.. contents:: :local:

Outgoing email
--------------

Outgoing email originates in the comm panel.  The comm panel is outside the scope of this document, but after an admin writes an email and selects recipients, the website creates a signle ``MessageRequest`` object with that data -- the email template, the list of students to which it will be sent, and some metadata like the sender.  (The ``MessageRequest`` model, and the others described below, are in ``esp/esp/dbmail/models.py``.)  

Then, every 15 minutes at most (exact timing depends on the site), cron runs ``esp/dbmail_cron.py``.  This does two things.  First, it looks for unprocessed ``MessageRequest`` objects.  For each ``MessageRequest``, and for each user to which it is sent, the script creates a ``TextOfEmail`` object, which contains the email text exactly as it will be sent (as well as the subject, recipient address, and such).  It then marks the ``MessageRequest`` as processed.

After ``MessageRequest`` processing is complete, ``esp/dbmail_cron.py`` looks for unsent ``TextOfEmail`` objects.  For each one, it  sends the email, then marks the request as sent.  To send the email we use `the standard Django facilities <https://docs.djangoproject.com/en/dev/topics/email/>`_, which construct the full email headers and message body, and, according to our settings, pass it via `SMTP <https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol>`_ to Exim, our MTA (Mail Transport Agent), which passes it on to the world (again via SMTP).

Incoming email
--------------

Incoming email is received by Exim via SMTP, and handled according to the settings in ``/etc/exim4``.  For mail at chapter-site domains, this mail is passed to the site's ``esp/mailgates/mailgate.py``.  This, in turn, consults the ``EmailList`` objects in the database (which on most sites are just the autocreated ones).

Each ``EmailList`` matches some regular expression of email addresses, and forwards the email to some list of users based on that.  (For example, class email lists match ``<emailcode>-students@``, and send to the class's students, teachers, and the admin archive list.)  Once we determine to whom to forward the email, we again use the standard Django facilities to send a copy to Exim, which passes it on to the world.
