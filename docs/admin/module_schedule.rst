==========================================
Program Module Schedule & Permission Dates
==========================================

.. contents:: :local:

Overview
========
The Program Module Management System allows administrators to configure registration schedules and operational time windows for Students, Teachers, and Volunteers. In ESP, module availability and registration timing are controlled via:

1. **Program Permissions**: Permission records associated with start and end dates (``start_date`` and ``end_date``) assigned to Django auth Groups (``Student``, ``Teacher``, ``Volunteer``).
2. **Program Module Objects** (``ProgramModuleObj``): Subclasses of ``ExpirableModel`` that store module-specific sequence numbers (``seq``), requirement settings (``required``, ``required_label``), and active time boundaries (``start_date`` and ``end_date``).

When a new program is created, initial role permissions are generated from the program setup form dates. ``ProgramModuleObj`` records are created lazily by ``Program.getModules()``/``getFromProgModule()``, and their ``start_date``/``end_date`` default to ``NULL`` unless explicitly set (e.g., via the module schedule API).

Model Architecture: ExpirableModel Subclass
===========================================
``ProgramModuleObj`` subclasses ``ExpirableModel``, providing every module record with native, time-aware windowing:

* ``start_date``: Nullable ``DateTimeField``. Indicates when the module opens for users.
* ``end_date``: Nullable ``DateTimeField``. Indicates when the module closes.
* ``NULL`` handling: A ``NULL`` timestamp is interpreted as "no expiry" (always open from that boundary).
* ``is_valid(when=None)``: Helper method that evaluates whether a module object is active at a given timestamp.

ProgramModuleObj Model Fields
------------------------------
The complete set of fields on a ``ProgramModuleObj`` record:

+--------------------+------------------------------+----------------------------------------------------------+
| Field              | Type                         | Description                                              |
+====================+==============================+==========================================================+
| ``program``        | ForeignKey (Program)         | The program this module object belongs to.               |
+--------------------+------------------------------+----------------------------------------------------------+
| ``module``         | ForeignKey (ProgramModule)   | The module definition (handler, module_type, seq).       |
+--------------------+------------------------------+----------------------------------------------------------+
| ``seq``            | IntegerField                 | Display order (ascending). Drag-to-reorder in timeline.  |
+--------------------+------------------------------+----------------------------------------------------------+
| ``required``       | BooleanField                 | If True, users are forced through this step first.       |
+--------------------+------------------------------+----------------------------------------------------------+
| ``required_label`` | CharField (80)               | Optional text to clarify requirement (e.g. "For minors") |
+--------------------+------------------------------+----------------------------------------------------------+
| ``link_title``     | CharField (64)               | Override for module's display link title. Leave blank    |
|                    |                              | to use the module's default.                             |
+--------------------+------------------------------+----------------------------------------------------------+
| ``start_date``     | DateTimeField (nullable)     | When module opens. NULL = no start constraint.           |
+--------------------+------------------------------+----------------------------------------------------------+
| ``end_date``       | DateTimeField (nullable)     | When module closes. NULL = no end constraint.            |
+--------------------+------------------------------+----------------------------------------------------------+

Backward Compatibility & Migration Strategy
-------------------------------------------
Subclassing ``ExpirableModel`` maintains complete backward compatibility across existing program installations:

* Non-destructive database migration adds nullable ``start_date`` and ``end_date`` columns.
* Pre-existing ``ProgramModuleObj`` records retain ``NULL`` values, interpreting them as indefinitely open with zero disruption to active programs.

Module Type Reference
---------------------
Every ``ProgramModule`` has a ``module_type`` field that determines the URL prefix and registration phase it belongs to:

+----------------+-----------------------------------------------+-----------------------------+
| ``module_type``| URL Prefix                                    | Registration Role           |
+================+===============================================+=============================+
| ``learn``      | ``/learn/<program>/<instance>/*``             | Student registration        |
+----------------+-----------------------------------------------+-----------------------------+
| ``teach``      | ``/teach/<program>/<instance>/*``             | Teacher registration        |
+----------------+-----------------------------------------------+-----------------------------+
| ``volunteer``  | ``/volunteer/<program>/<instance>/*``         | Volunteer registration      |
+----------------+-----------------------------------------------+-----------------------------+
| ``manage``     | ``/manage/<program>/<instance>/*``            | Admin/management pages      |
+----------------+-----------------------------------------------+-----------------------------+
| ``onsite``     | ``/onsite/<program>/<instance>/*``            | Day-of onsite operations    |
+----------------+-----------------------------------------------+-----------------------------+

Time-Filtering in Program.getModules()
---------------------------------------
To maintain high performance without returning stale registration views:

1. ``Program.getModules()`` retrieves the program's module objects list from the Memcached layer.
2. The ``is_valid()`` filter is evaluated dynamically in the request path after cache retrieval.
3. Cache invalidation on ``save()`` guarantees instant propagation of schedule edits while avoiding database query overhead during active registration.

Initial Permission and Date Generation
======================================
When creating a program via the new program form (or invoking ``prepare_program()`` directly in code), the system populates initial student/teacher permission records based on the program form dates.

Program Form Date Fields
------------------------
The new program setup form collects four primary date boundaries:

* ``student_reg_start``: Opening timestamp for student registration.
* ``student_reg_end``: Closing timestamp for student registration.
* ``teacher_reg_start``: Opening timestamp for teacher registration.
* ``teacher_reg_end``: Closing timestamp for teacher registration.

Default Core Permissions
------------------------
By default, ``prepare_program()`` generates base role permissions for students and teachers:

* ``Student/All``: Dated with ``student_reg_start`` and ``student_reg_end``.
* ``Student/Profile``: Starts on ``student_reg_start``.
* ``Teacher/All``: Dated with ``teacher_reg_start`` and ``teacher_reg_end``.
* ``Teacher/Classes/View``, ``Teacher/MainPage``, ``Teacher/Profile``: Start on ``teacher_reg_start``.

Module-Associated Permission Generation
---------------------------------------

Module-specific permission dates are also generated during ``prepare_program()``. The module handler's ``permission_types``/``get_permission_types()`` are inspected and matching program-level ``Permission`` records for the inferred role group are created. These ``Permission`` records synchronized whenever ``ProgramModuleObj.sync_permissions()`` is invoked (for example, after updating a module's ``start_date``/``end_date`` through the module schedule update API).

Module Object Date Inheritance (ProgramModuleObj)
=================================================
When ``Program.getModules()`` is invoked, the system initializes ``ProgramModuleObj`` instances for each enabled module in the program.

How Dates Are Inherited
-----------------------
During creation of a new ``ProgramModuleObj`` in ``getFromProgModule()``:

1. If cloning from a previous program instance, sequence numbers, requirement flags, and dates are copied from the previous ``ProgramModuleObj``.
2. For fresh program modules, initial dates are populated from matching program ``Permission`` records:

   * The module handler's permission types are determined.
   * The module type (``learn``, ``teach``, ``volunteer``) maps to the corresponding user role group (``Student``, ``Teacher``, ``Volunteer``).
   * The system queries matching ``Permission`` records for the program filtering on:

     * ``program=prog``
     * ``permission_type__in=perm_types``
     * ``user__isnull=True``
     * ``user_filter__isnull=True``
     * Matching Django auth ``Group`` (``role``)

   * If a matching permission record is found, ``BaseModule.start_date`` and ``BaseModule.end_date`` are set to ``perm.start_date`` and ``perm.end_date``.

Module Schedule APIs & Admin Interactions
=========================================
The module schedule functionality is currently exposed via JSON endpoints under ``/manage/<program_type>/<program_term>/module_schedule/`` (see the "Module Schedule API Reference" section below). These endpoints support listing modules, updating ``start_date``/``end_date``/metadata, previewing active modules at a given time, detecting conflicts, and bulk reordering.

Bidirectional Permission Sync (sync_permissions)
================================================
When a ``ProgramModuleObj``'s ``start_date`` or ``end_date`` is updated via the module schedule update API, the ``sync_permissions()`` method is invoked to propagate date changes back to the backend ``Permission`` table. (Edits made directly in the Django admin do not currently call ``sync_permissions()`` automatically.)

1. Retrieves ``permission_types`` from the module handler.
2. Determines the correct Django auth ``Group`` (``Student``, ``Teacher``, ``Volunteer``) by inspecting the ``permission_type`` prefix or falling back to ``module_type``.
3. If a matching ``Permission`` record exists for the program+role+type, it is updated via ``perms.update(start_date=..., end_date=...)``. If none exists, a new ``Permission`` record is created.
4. Logs a warning if the role cannot be determined or the Group does not exist, then continues (non-fatal).

This ensures the module schedule and the permission deadline system remain **fully in sync** regardless of which interface the administrator uses.

Permission Types per Module Handler
------------------------------------
Key handler classes and their ``permission_types``:

+-------------------------------------------+------------------------------------+
| Handler Class                             | permission_types                   |
+===========================================+====================================+
| ``StudentClassRegModule``                 | ``Student/Classes``                |
+-------------------------------------------+------------------------------------+
| ``TeacherClassRegModule``                 | ``Teacher/Classes/All``            |
+-------------------------------------------+------------------------------------+
| ``RegProfileModule``                      | ``Student/Profile``,               |
|                                           | ``Teacher/Profile``                |
+-------------------------------------------+------------------------------------+
| ``AvailabilityModule``                    | ``Teacher/Availability``           |
+-------------------------------------------+------------------------------------+
| ``StudentRegPhaseZero``                   | ``Student/PhaseZero``              |
+-------------------------------------------+------------------------------------+
| ``StudentAcknowledgementModule``          | ``Student/Acknowledgement``        |
+-------------------------------------------+------------------------------------+
| ``TeacherAcknowledgementModule``          | ``Teacher/Acknowledgement``        |
+-------------------------------------------+------------------------------------+
| ``VolunteerSignup``                       | ``Volunteer/Signup``               |
+-------------------------------------------+------------------------------------+
| ``StudentRegConfirm``                     | ``Student/Confirm``                |
+-------------------------------------------+------------------------------------+
| ``StudentLunchSelection``                 | ``Student/Classes/Lunch``          |
+-------------------------------------------+------------------------------------+
| ``StudentSurveyModule``                   | ``Student/Survey``                 |
+-------------------------------------------+------------------------------------+
| ``TeacherSurveyModule``                   | ``Teacher/Survey``                 |
+-------------------------------------------+------------------------------------+

Module Questions Integration
============================
The timeline's side panel reuses the module group structure from the Module Questions interface:

* Enabling a module group in the timeline automatically instantiates the corresponding ``ProgramModuleObj`` records with ``start_date = now()`` and syncs with the questions interface.
* Disabling a module group prompts for student activity confirmation before issuing a deletion request.

Accessibility & Keyboard Navigation (WCAG 2.1 AA)
=================================================
The module schedule interface meets full WCAG 2.1 AA accessibility standards:

* **ARIA Roles**: Handles use ``role="slider"`` with ``aria-valuemin``, ``aria-valuemax``, and ``aria-valuenow``. Module rows use ``role="group"``.
* **Keyboard Navigation**:

  * ``Tab`` / ``Shift+Tab`` moves focus across timeline controls.
  * ``Arrow Left`` / ``Arrow Right`` adjusts dates by 1 hour (or 1 day with ``Shift``).
  * ``Alt+Up`` / ``Alt+Down`` reorders row sequence positions.

* **Live Announcements**: An ``aria-live="polite"`` region announces updated dates during drag and keyboard nudging.

Conflict Detection & Special Guards
====================================

Special-Case Handler Guards
---------------------------
Certain modules require continuous availability or locked sequencing:

* ``always_enabled = True``: Handler class property indicating the module remains active regardless of timestamp.
* ``seq_locked = True``: Handler class property preventing reordering of the module sequence position.

Schedule Conflict Detection Engine
-----------------------------------
Phase-based registration programs use mutual exclusion rules (e.g. lottery signup and FCFS registration cannot run concurrently):

* Handlers declare conflicting modules via a ``conflicts_with`` class attribute.
* The ``/manage/<program_type>/<program_term>/module_schedule/conflicts/`` endpoint scans module time windows and reports overlaps for handlers that declare conflicts via the ``conflicts_with`` class attribute.

Module Schedule API Reference
=============================
The module management interface interacts with the backend via REST/AJAX endpoints:

* ``GET /manage/<program_type>/<program_term>/module_schedule/``: Returns JSON payload of program module objects grouped by ``module_type``.
* ``POST /manage/<program_type>/<program_term>/module_schedule/update/``: Updates ``start_date``, ``end_date``, ``seq``, and other editable fields for a module object.
* ``POST /manage/<program_type>/<program_term>/module_schedule/reorder/``: Bulk updates ``seq`` for multiple module objects.
* ``GET /manage/<program_type>/<program_term>/module_schedule/conflicts/``: Returns scheduling conflicts and overlapping time windows as JSON.
* ``GET /manage/<program_type>/<program_term>/module_schedule/preview/?at=<timestamp>``: Previews modules active at a given time.

Testing Guidelines & Verification
=================================
Unit tests for the module schedule endpoints and conflict detection reside in ``esp/esp/program/modules/tests/``:

* ``test_module_schedule_api.py``: Validates auth, listing modules, updating dates/metadata, and preview behavior.
* ``test_module_schedule_conflicts_api.py``: Validates conflict detection based on ``conflicts_with`` and time-window overlap.
* **Auth Group Setup**: Fresh test databases must invoke ``user_role_setup()`` to seed role groups before committing program permissions.

Developer Reference & File Locations
====================================

* **Program Setup Utility**: ``esp/esp/program/setup.py`` (``prepare_program``, ``commit_program``)
* **Module Base & Factory**: ``esp/esp/program/modules/base.py`` (``getFromProgModule``, ``ProgramModuleObj``)
* **Unit Test Suite**: ``esp/esp/program/tests.py`` (``NewProgramModulePermissionsTest``)
