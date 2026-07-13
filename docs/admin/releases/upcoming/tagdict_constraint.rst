TagDict Global Tag Constraint - Database Portability
=====================================================

The ``tagdict`` app now enforces unique constraints for global tags across all supported database backends (PostgreSQL, SQLite, and MySQL), improving data integrity and database portability.

Background
----------

Previously, the unique constraint for global tags (tags where both ``content_type`` and ``object_id`` are NULL) was only enforced on PostgreSQL through a custom SQL file. This meant that other database backends could potentially allow duplicate global tags, leading to data integrity issues.

What Changed
------------

The constraint is now implemented through:

1. **Database-level constraints** via a Django migration that automatically detects the database backend and applies the appropriate constraint:
   
   - PostgreSQL and SQLite use partial indexes (most efficient)
   - MySQL uses a generated column workaround

2. **Model-level validation** as a fallback to ensure data integrity even on databases that don't support partial indexes

Impact
------

- **For Administrators**: No action required for new deployments. Existing deployments should check for duplicate global tags before running migrations (see technical documentation).

- **For Developers**: The constraint is now enforced consistently across all database backends, preventing duplicate global tags at both the database and application levels.

- **For Database Portability**: The codebase is now more portable and can work reliably with PostgreSQL, SQLite, or MySQL without backend-specific behavior.

Technical Details
-----------------

- Migration: ``esp/esp/tagdict/migrations/0002_add_global_tag_unique_constraint.py``
- Model validation added to ``Tag.clean()`` and ``Tag.save()``
- Comprehensive tests added to verify constraint enforcement
- Legacy PostgreSQL-specific SQL file removed

For detailed technical documentation, see ``TAGDICT_CONSTRAINT_CHANGES.md`` in the repository root.

Related Issues
--------------

- GitHub Issue #4121
