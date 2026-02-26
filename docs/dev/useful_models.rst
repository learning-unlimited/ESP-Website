Commonly Used Models
====================
Since `this picture <models.png>`_ may not be the most useful way to figure out what model does what you want, here’s a list of the most commonly used ones:

* ``esp.users.models.ESPUser``: This is a proxy model over ``django.contrib.auth.User`` (the standard user account model). Proxy model basically means it attaches extra methods, but not extra fields.
* ``django.contrib.auth.models.Group``: Keeps track of types of users, like Student and Teacher.
* ``esp.users.models.Permission``: Permissions for various parts of the website; can be applied to a particular ESPUser or Group.
* ``esp.users.models.{StudentInfo,TeacherInfo,ContactInfo}``: Various types of extra information associated with various types of users.
* ``esp.program.models.Program``: An instance of a program, like Splash Fall 2014.
* ``esp.program.models.class_.ClassSubject``: A class, like "X9002: Steak: Theory and Practice".
* ``esp.program.models.class_.ClassSection``: A section of a class, like X9002s1.
* ``esp.program.models.RegistrationProfile``: An instance of the profile information that students fill out before registering for a program.
* ``esp.program.models.StudentRegistration``: A student’s registration for or interest in a ClassSection, like "benkraft marked X9002s1 as Priority/1".
* ``esp.program.models.StudentSubjectInterest``: A student’s interest in a ClassSubject (correspond to stars in the two-phase lottery).
* ``esp.cal.models.Event``: A timeblock (or sometimes another timed event such as a teacher training), associated with a program.
* ``esp.resources.models.Resource``: A resource, like a classroom or the LCD projector in a classroom.  Note``: the resources models are a bit of a mess, and we’re working on rewriting them.
* ``esp.accounting.models.LineItemType``: A type of payment, such as "Saturday Lunch for Splash Fall 2014 ($5)"
* ``esp.tagdict.models.Tag``: A generic key/value pair, optionally associated to another object in the database (most commonly a Program).  Commonly used for settings.
