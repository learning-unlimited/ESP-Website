ESP Email Setup
===============

This document describes how email, both incoming and outgoing, makes its way where it's going on the ESP website.  The code will serve as a more specific reference for the details, but this is an overview of the high-level setup.  Note: this document describes the setup on the LU production server; the parts of the setup outside the ESP-Website codebase may vary slightly on sites hosted elsewhere (in particular, esp.mit.edu).

.. contents:: :local:

Outgoing email
--------------

User-generated outgoing email originates in the comm panel.  The comm panel is outside the scope of this document, but after an admin writes an email and selects recipients, the website creates a single ``MessageRequest`` object with that data -- the email template, the list of students to which it will be sent, and some metadata like the sender.  (The ``MessageRequest`` model, and the others described below, are in ``esp/esp/dbmail/models.py``.)

Then, every 15 minutes at most (exact timing depends on the site), cron runs ``esp/dbmail_cron.py``.  This does two things.  First, it looks for unprocessed ``MessageRequest`` objects.  For each ``MessageRequest``, and for each user to which it is sent, the script creates a ``TextOfEmail`` object, which contains the email text exactly as it will be sent (as well as the subject, recipient address, and such).  It then marks the ``MessageRequest`` as processed.

After ``MessageRequest`` processing is complete, ``esp/dbmail_cron.py`` looks for unsent ``TextOfEmail`` objects.  For each one, it sends the email, then marks the request as sent.  Sending goes through ``esp.dbmail.models.send_mail``, which builds the message and hands it to Django's configured ``EMAIL_BACKEND`` (on LU sites this is ``django-sendgrid-v5``, which posts to the SendGrid Web API).

``send_mail`` also requires the ``From`` address to be on the site's own domain, on ``learningu.org``, or on a subdomain of it; adds one-click ``List-Unsubscribe`` headers when a ``user`` is supplied; and removes duplicate recipient addresses.

Incoming email
--------------

Incoming email is received by Exim, our Mail Transport Agent (MTA), via `SMTP <https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol>`_ and handled according to the settings in ``/etc/exim4``.  For mail at chapter-site domains, Exim pipes the message to the site's ``esp/mailgates/mailgate.py``, with ``LOCAL_PART`` set to the part of the recipient address before the ``@``.  Everything described below happens in that script.

Routing
~~~~~~~

Routing is done on ``LOCAL_PART`` -- the envelope recipient Exim delivered to.  That local part is matched against the ``regex`` of each ``EmailList`` in the database, in ``seq`` order; the first handler that accepts it delivers the message.  Handlers live in ``esp/esp/dbmail/receivers/``.  The four autocreated ``EmailList`` entries are:

* ``SectionList`` -- ``<emailcode>s<n>-class``, ``-teachers`` or ``-students``, delivering to the teachers and/or students of that section (plus the program directors).
* ``ClassList`` -- ``<emailcode>-class``, ``-teachers`` or ``-students``, delivering to the teachers and/or students of that class  (plus the program directors).
* ``PlainList`` -- any address with a matching ``PlainRedirect``, delivering to that redirect's destinations.
* ``UserEmail`` -- a username, delivering to that user's own email address.

Each ``EmailList`` may also set ``subject_prefix``, ``from_email``, and ``cc_all`` (send one message naming every recipient, rather than a separate copy to each).

Who may send
~~~~~~~~~~~~

The ``From`` address must belong to an account on the site.  Where several accounts share that address, the most privileged one is used: administrator, then teacher, then the earliest account created.

``UserEmail`` applies a further rule.  An alias belonging to a teacher or administrator accepts mail from any registered sender; anyone else's alias accepts mail only from a teacher or administrator.  This keeps students reachable by their own teachers while leaving them unreachable by other senders.  On sites with ``USE_MAILMAN`` set, messages carrying a ``List-Id`` header are also accepted.

Headers
~~~~~~~

Before a message goes out, its ``From`` is replaced with the sender's ``username@<site domain>`` alias.  This aligns the message with the DKIM signature the site applies, so it passes DMARC at the recipient, and it keeps the sender's personal address out of the forwarded copy.  A ``From`` already on one of the site's own domains is left alone.  Replies to the alias re-enter the mailgate and resolve back to the sender.

Group broadcasts (i.e., everything except ``UserEmail``) also get:

* ``Reply-To`` set to the list address, so replies return to the list rather than to the sender personally.  Where the sender is not on that list themselves (e.g., an administrator writing to a class's teacher list), their alias is added alongside it.
* the ``EmailList``'s ``subject_prefix`` and the class's emailcode prepended to the subject, unless the subject already carries them.
* a fresh ``Message-ID``, so that a recipient who receives a message by more than one route sees both copies.

Every delivery appends a ``Delivered-To`` header naming the address it was delivered to to prevent future loops.

Bounces
~~~~~~~

When no handler delivers a message, an "undeliverable" notice goes back to the sender, provided they have an account on the site.  Notices are limited to one per sender per ``MAILGATE_BOUNCE_INTERVAL`` seconds (default 24 hours; set to ``0`` to disable), which prevents a forged ``From`` being used to aim a run of them at one user.

Configuration
~~~~~~~~~~~~~

``MAILGATE_EMAIL_BACKEND`` selects how forwarded mail is sent.  It defaults to Django's SMTP backend and reads ``EMAIL_HOST``, ``EMAIL_PORT``, ``EMAIL_HOST_USER``, ``EMAIL_HOST_PASSWORD`` and ``EMAIL_USE_TLS``.  A site delivering through a local MTA needs nothing further; a site relaying through SendGrid sets those to ``smtp.sendgrid.net``, ``587``, ``apikey``, the API key, and ``True``, respectively.  It must be an SMTP-style backend, since forwarding transmits the original message unchanged.

A chapter that sends from a shared mailbox, such as a chapter Gmail account, should have an account on the site carrying that address and the administrator role.  That lets the address pass the sender check, gives it an alias for the ``From`` rewrite, and lets replies to that alias reach it.

SendGrid Configuration
----------------------
Modern email providers require us to prove we are who we say we are by authenticating our domains (registered with Gandi and/or Amazon Web Services (AWS)) with our email provider(s), currently SendGrid. This process requires two steps: telling the email provider what domains we own and confirming that we own them by posting a unique record (that the email service gives us) to the domain registrar. See ``/lu/scripts/sendgrid_authentication.py`` to set everything up automatically with SendGrid and AWS.
