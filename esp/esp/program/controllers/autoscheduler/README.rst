Autoscheduler Controller
========================

Introduction
------------

This is a controller for an automatic scheduling utility. The current use for
this is an automatic scheduling assistant, intended for use in parallel with
the AJAX scheduler to find good scheduling choices for individual sections,
but the backend is flexible and should be easy to turn into a (albeit slow)
autoscheduler if need be.

Overview
--------

Relationship with Database Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The controller is designed to read from the database to an in-memory
representation of a schedule; most of the controller (excepting the DB
interface and the part that interacts with the frontend) only operates on this
in-memory representaton and is oblivious to the database and its models.
Consequently, if the database models change, you only need to update the DB
interface to correctly translate from the new model to the in-memory
representation.

Schedule Manipulations
~~~~~~~~~~~~~~~~~~~~~~

Allowed manipulations to a given schedule are:

* Schedule a currently-unscheduled class

* Unschedule a currently-scheduled class

* Move a currently-scheduled class

* Swap two currently-scheduled classes

Strictly speaking, all possible schedule changes can be achieved by a
combination of scheduling and unscheduling alone. Adding additional move and
swap manipulations, however, can achieve better results when you do something
like "give me the best possible schedule achievable within 2 manipulations".

Note that while the schedule manipulator theoretically supports the Swap
manipulations, the current schedule optimizer (search.py) doesn't use it, so it is
largely untested and there are probably bugs somewhere.

Optimization
~~~~~~~~~~~~

The controller is essentially agnostic to the optimization algorithm used. The
current optimization algorithm is in search.py, but alternative algorithms can
be implemented and plugged into the controller as well. (The interface with
the frontend, i.e. controller.py, determines which optimizer is used.)

Configuration
~~~~~~~~~~~~~

The automatic scheduling utility has various options to e.g. control the
weights of the different scorers used. There are default options specified in
code, which are in turn overridden by options read from various Tags, which
are in turn overridden by inputs from the frontend.

Layout
------

Below is a summary of the different components of the controller. Each file
itself contains more detailed documentation.

config.py
~~~~~~~~~

Various configuration options are here. Modify default options, descriptions,
or turn on the timer instrumentation (and others).

consistency_checks.py
~~~~~~~~~~~~~~~~~~~~~

A class containing checkers for invariants about the in-memory schedule that
are not expected to be violated, e.g. "these two data structures which
represent the same information in different ways should agree with each
other". This is mostly a safety net in case the implementation is buggy.

Consistency checks are run when the schedule is first loaded into memory and
again when it is saved.

constraints.py
~~~~~~~~~~~~~~

Various classes for requirements like "teachers can't teach two classes at
once". Each constraint class can:

* Verify that an existing schedule satisfies the constraints

* Determine whether a given schedule manipulation would cause the constraint to
  be violated for a given schedule

If a constraint is violated, the constraint class returns a
ConstraintViolation, otherwise it returns None. This is more helpful than
returning a boolean for debugging purposes.

Constraints can be "required" or "optional". A required constraint is one that
is assumed to hold or would otherwise lead to adverse behavior if violated,
e.g. trying to double-book a room would probably either lead to a crash or to
silently unscheduling whatever was already in that room. An optional constraint
is something like "don't schedule a class over every block of lunch in any
given day".

Constraints are checked when a schedule is loaded into memory, before it is
saved, and before any schedule manipulation (i.e. before scheduling a section,
check that doing so wouldn't violate any constraints).

To implement a new constraint, define it in this file as a subclass of
BaseConstraint and update config.py with a description and default for whether
to enable it or not.

controller.py
~~~~~~~~~~~~~

Interfaces between the frontend module and the rest of the controller.
Essentially all of the control happens here, i.e. constructing the optimizer,
manipulator, schedule, etc. with all of the provided parameters. If you want
to swap out a module with another one, e.g. change the optimization algorithm,
this is probably where you should make the change.

db_interface.py
~~~~~~~~~~~~~~~

This defines the interface between the database models used by the rest of the
ESP Website and the in-memory representation used by the rest of the
controller. In other words, it implements loading a schedule from the database
and saving a schedule back into the database.

With the exception of controller.py, the rest of the controller
should be oblivious to the database (and also should not call any db_interface
functions).

exceptions.py
~~~~~~~~~~~~~

(Trivial) definitions of exceptions used by the controller.

manipulator.py
~~~~~~~~~~~~~~

Implements the schedule/unschedule/move/swap manipulations. Keeps track of a
history of manipulations performed and allows actions to be undone. History can
also be rendered into or replayed from a JSON object.

data_model.py
~~~~~~~~~~~~~

Defines the in-memory representation of a schedule.

resource_checker.py
~~~~~~~~~~~~~~~~~~~

Defines classes for representing (relatively) complex user-defined constraints
or scorers on furnishings and classroom names.

In particular, this defines a (mostly) human-readable specification language
and translates from it to criteria of the flavor "if a section asks for a
specific resource, the classroom should have it" (or vice versa, or this
applies to every section, or the classroom's name should match a certain
pattern). See ResourceCriterion.create_from_specification() for more details.

ResourceCriteria can be used either as constraints (constraints.py) or scorers
(scorers.py), as parameters to the ResourceCriteriaConstraint and
ResrouceCriteriaScorer, respectively.

A small number of default ResourceCriteria are defined in config.py; the
remainder are loaded from Tags. Note that ResourceCriteria are only for
*special* constraints; in particular, a Scorer already exists for the typical
"if a section requests a resource, the classroom should have it" and "if a
section requests a resource with a particular value, the classroom should have
it".

scoring.py
~~~~~~~~~~

A Scorer rates how "good" a schedule is along a particular axis. Different
Scorers are aggregated together in a weighted average into a CompositeScorer.

Each scorer:

* Stores internal state to represent the relevant aspects of the current
  schedule

* Can return the current score associated with its internal state

* Can update its internal state due to a schedule manipulation

Scorers are expected to return a score in the range [0, 1] where 0 is bad and 1
is good. Scorers also maintain a scaling factor, such that when its score is
multiplied by the scaling factor, each schedule manipulation affecting a single
section will on average have impact (1 / num_sections), where this average
ignores manipulations which don't affect the scorer. For example, a scorer like
"maximize the number of sections scheduled" has scaling factor of 1, and a
scorer like "schedule as many distinct teachers as possible" has scaling factor
(num_teachers / num_sections), because each time a new teacher is scheduled
they impact the score by (1 / num_teachers).

To implement a new Scorer, implement it here as a subclass of BaseScorer,
making sure to override the scaling factor as needed, and update config.py
with a description and default weight.

Note that Scorers are intended to be sufficiently comprehensive that every
scheduling check should have a scorer associated with it.

search.py
~~~~~~~~~

Contains a brute-force-search optimization algorithm targeting a particular
section.  The algorithm is as follows:

Given a particular section to optimize and a bounded depth:

* Consider every possible place and time to schedule the section.

* For every place and time, if it does not violate any constraints, unschedule
  all sections which currently occupy those rooms at those timeslots and
  schedule the target section there.

* For every section we have unscheduled in this way, recurse (unless we have
  reached the maximum depth).

* Ignore all possibilities which caused a section to be unscheduled without
  being re-scheduled.

* Return the possibility which produces the best score.

This is implemented as a DFS as a consequence of how scoring and constraints
operate (i.e. as a part of the search procedure, we perform and undo
manipulations to the given schedule).

This search procedure will (by design) never unschedule an existing section
(but it might move them). Empirically, the search procedure terminates within
a few seconds for depth 2 on a devserver on a reasonably fast computer or
depth 3 on MIT's server.

Conceptually, this search procedure can be modified into a full autoscheduler
with minimal effort (i.e. for each section, optimize it using this optimizer)
but this was never implemented because there was lack of interest in using it.

testutils.py
~~~~~~~~~~~~

Contains helper functions for writing unit tests (by generating schedules (the
in-memory kind, not the database kind)) for you.

util.py
~~~~~~~~

Contains miscellaneous helper functions, including a timer which is enabled or
disabled via config.py, intended to pinpoint bottlenecks in the code.
It should be disabled for production, and the output of the timer is not
automatically reported anywhere. If in the course of development you want to
read the results of the timer, you should use the get_recorded_times and
print_recorded_times functions implemented in manipulator.py (it's possible
you can also get it to work by importing util.py and reading TIMER directly,
but it didn't work the one time I tried it).
