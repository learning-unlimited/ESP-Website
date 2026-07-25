# TagDict Global Tag Unique Constraint Implementation

## Overview

This document describes the changes made to enforce a unique constraint on global tags in the `tagdict` app, making it database-agnostic and consistent across PostgreSQL, SQLite, and MySQL.

## Problem Statement

Previously, the `tagdict` app enforced a partial unique index for global tags using PostgreSQL-specific SQL:

```sql
CREATE UNIQUE INDEX tagict_tag_unique_notpertarget
ON tagdict_tag (key)
WHERE NOT (content_type IS NULL OR object_id IS NULL);
```

This constraint was only implemented for PostgreSQL via a custom SQL file (`tag.postgresql.sql`), which meant:

- Other database backends (SQLite, MySQL) did not enforce this constraint
- Data integrity could be compromised on non-PostgreSQL databases
- The codebase had backend-specific behavior

## Solution Implemented

The solution consists of three layers of protection:

### 1. Database-Level Constraint (Migration)

**File:** `esp/esp/tagdict/migrations/0002_add_global_tag_unique_constraint.py`

This migration adds a unique constraint for global tags using database-specific SQL:

- **PostgreSQL & SQLite:** Uses partial indexes (most efficient)

  ```sql
  CREATE UNIQUE INDEX tagdict_tag_unique_global
  ON tagdict_tag (key)
  WHERE content_type_id IS NULL AND object_id IS NULL;
  ```

- **MySQL:** Uses a generated column workaround (MySQL doesn't support partial indexes)

  ```sql
  ALTER TABLE tagdict_tag
  ADD COLUMN global_tag_key VARCHAR(50) AS (
      CASE
          WHEN content_type_id IS NULL AND object_id IS NULL THEN `key`
          ELSE NULL
      END
  ) STORED;

  CREATE UNIQUE INDEX tagdict_tag_unique_global
  ON tagdict_tag (global_tag_key);
  ```

### 2. Model-Level Validation

**File:** `esp/esp/tagdict/models.py`

Added `clean()` and modified `save()` methods to the `Tag` model:

```python
def clean(self):
    """
    Validate that global tags have unique keys.
    Provides fallback for databases without partial index support.
    """
    super().clean()

    if self.content_type is None and self.object_id is None:
        existing = Tag.objects.filter(
            key=self.key,
            content_type__isnull=True,
            object_id__isnull=True
        ).exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError({
                'key': f'A global tag with key "{self.key}" already exists.'
            })

def save(self, *args, **kwargs):
    """Override save to call full_clean() for validation."""
    if not kwargs.pop('skip_validation', False):
        self.full_clean()
    super().save(*args, **kwargs)
```

This ensures data integrity even if the database constraint is not supported or fails.

### 3. Comprehensive Tests

**File:** `esp/esp/tagdict/tests.py`

Added two new test methods to `TagTest`:

1. **`testGlobalTagUniqueConstraint`**: Verifies that duplicate global tags are prevented
2. **`testPerObjectTagsNotAffectedByGlobalConstraint`**: Ensures per-object tags can still have duplicate keys

## Changes Made

### Files Modified

1. **`esp/esp/tagdict/models.py`**
   - Added `ValidationError` import
   - Added `clean()` method for validation
   - Modified `save()` method to call `full_clean()`
   - Updated Meta class comment to reflect new implementation

2. **`esp/esp/tagdict/tests.py`**
   - Added `ValidationError` and `IntegrityError` imports
   - Added `testGlobalTagUniqueConstraint()` test
   - Added `testPerObjectTagsNotAffectedByGlobalConstraint()` test

### Files Created

1. **`esp/esp/tagdict/migrations/0002_add_global_tag_unique_constraint.py`**
   - New migration implementing database-specific constraints

### Files Deleted

1. **`esp/esp/tagdict/tag.postgresql.sql`**
   - Removed legacy PostgreSQL-specific SQL file (no longer needed)

## Testing

### Running Tests

To test the implementation, run:

```bash
# Test all tagdict tests
python manage.py test esp.tagdict.tests

# Test only the new constraint tests
python manage.py test esp.tagdict.tests.TagTest.testGlobalTagUniqueConstraint
python manage.py test esp.tagdict.tests.TagTest.testPerObjectTagsNotAffectedByGlobalConstraint
```

### Using Docker

If using Docker for development:

```bash
# Run tests in Docker container
docker-compose run web python manage.py test esp.tagdict.tests

# Or enter the container and run tests
docker-compose run web bash
python manage.py test esp.tagdict.tests
```

### Manual Testing

You can also test manually in the Django shell:

```python
from esp.tagdict.models import Tag
from django.core.exceptions import ValidationError
from django.db import IntegrityError

# Test 1: Create a global tag
Tag.setTag("test_global", target=None, value="first value")

# Test 2: Try to create a duplicate global tag (should fail)
try:
    tag = Tag(key="test_global", content_type=None, object_id=None, value="second value")
    tag.save()
    print("ERROR: Duplicate global tag was allowed!")
except (IntegrityError, ValidationError) as e:
    print(f"SUCCESS: Duplicate prevented - {e}")

# Test 3: Verify per-object tags still work
from django.contrib.auth.models import User
user1 = User.objects.first()
user2 = User.objects.last()

Tag.setTag("test_per_object", target=user1, value="value1")
Tag.setTag("test_per_object", target=user2, value="value2")
Tag.setTag("test_per_object", target=None, value="global")

print("SUCCESS: Per-object tags with same key work fine")

# Cleanup
Tag.unSetTag("test_global")
Tag.unSetTag("test_per_object", target=user1)
Tag.unSetTag("test_per_object", target=user2)
Tag.unSetTag("test_per_object", target=None)
```

## Migration Instructions

### For Existing Deployments

1. **Backup your database** before running migrations

2. **Check for existing duplicate global tags:**

   ```sql
   SELECT key, COUNT(*) as count
   FROM tagdict_tag
   WHERE content_type_id IS NULL AND object_id IS NULL
   GROUP BY key
   HAVING COUNT(*) > 1;
   ```

3. **If duplicates exist, resolve them manually:**

   ```python
   from esp.tagdict.models import Tag

   # Find duplicates
   duplicates = Tag.objects.filter(
       content_type__isnull=True,
       object_id__isnull=True
   ).values('key').annotate(count=Count('key')).filter(count__gt=1)

   # For each duplicate, keep one and delete others
   for dup in duplicates:
       tags = Tag.objects.filter(
           key=dup['key'],
           content_type__isnull=True,
           object_id__isnull=True
       ).order_by('id')

       # Keep the first one, delete the rest
       for tag in tags[1:]:
           tag.delete()
   ```

4. **Run the migration:**
   ```bash
   python manage.py migrate tagdict
   ```

### For New Deployments

Simply run migrations as normal:

```bash
python manage.py migrate
```

## Benefits

1. **Database Portability**: Works consistently across PostgreSQL, SQLite, and MySQL
2. **Data Integrity**: Prevents duplicate global tags at both database and application levels
3. **Backward Compatibility**: Preserves existing PostgreSQL behavior
4. **Robustness**: Multiple layers of protection (database + model validation)
5. **Maintainability**: Removes backend-specific SQL files in favor of Django migrations

## Technical Details

### Why This Approach?

- **Django 2.2 Limitations**: Django 2.2 doesn't support `UniqueConstraint` with Q() expressions (added in Django 3.0+)
- **RunPython vs RunSQL**: Using `RunPython` allows runtime detection of the database backend
- **Model Validation**: Provides a safety net for databases that don't support partial indexes
- **MySQL Workaround**: Generated columns are the standard MySQL approach for conditional uniqueness

### Database Compatibility

| Database   | Version Required | Implementation Method |
| ---------- | ---------------- | --------------------- |
| PostgreSQL | 9.0+             | Partial index         |
| SQLite     | 3.8.0+ (2013)    | Partial index         |
| MySQL      | 5.7+             | Generated column      |

## Future Improvements

When upgrading to Django 3.0+, this can be simplified using:

```python
from django.db.models import Q, UniqueConstraint

class Tag(models.Model):
    # ... fields ...

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['key'],
                condition=Q(content_type__isnull=True, object_id__isnull=True),
                name='tagdict_tag_unique_global'
            )
        ]
```

## Related Issues

- GitHub Issue: #4121
- Original TODO comment in `models.py` (now resolved)

## Contributors

This implementation addresses the issue raised in #4121 and follows Django best practices for database-agnostic constraint implementation.
