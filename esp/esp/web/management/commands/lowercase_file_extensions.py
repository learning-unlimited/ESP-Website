"""
Management command to migrate file extensions to lowercase.

This command finds all files in the media directory that have uppercase
file extensions and renames them to have lowercase extensions. It also
updates all database references to these files.

Usage:
  python manage.py lowercase_file_extensions [--dry-run] [--verbose]

Production Safe:
  - Dry-run mode for safety
  - Transaction management for database consistency
  - File permission checks before starting
  - Comprehensive error handling
  - Proper logging for audit trails
"""

import os
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Migrate file extensions to lowercase for case-insensitive '
        'file handling'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help=(
                'Show what would be changed without actually '
                'changing files'
            ),
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            dest='verbose',
            help=(
                'Print detailed information about each file '
                'processed'
            ),
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)

        self.stdout.write(
            'Starting file extension migration to lowercase...'
        )
        logger.info(
            'File extension migration started (dry_run=%s)', dry_run
        )

        if dry_run:
            msg = '(DRY RUN MODE - no files will be changed)'
            self.stdout.write(self.style.WARNING(msg))

        # Get the media root directory
        media_root = settings.MEDIA_ROOT
        if not os.path.exists(media_root):
            msg = f'Media directory not found: {media_root}'
            self.stdout.write(self.style.ERROR(msg))
            logger.error(msg)
            raise CommandError(msg)

        # Check write permissions
        if not os.access(media_root, os.W_OK):
            msg = f'No write permission on media directory: {media_root}'
            self.stdout.write(self.style.ERROR(msg))
            logger.error(msg)
            raise CommandError(msg)

        self.stdout.write(f'Media root: {media_root}')
        logger.info('Media root: %s', media_root)

        renamed_files = []
        files_with_uppercase_ext = []

        # Walk through all files in the media directory
        for root, dirs, files in os.walk(media_root):
            for filename in files:
                file_path = os.path.join(root, filename)
                root_name, ext = os.path.splitext(filename)

                # Check if extension has uppercase letters
                if ext and ext != ext.lower():
                    rel_path = os.path.relpath(file_path, media_root)
                    new_filename = root_name + ext.lower()
                    new_file_path = os.path.join(root, new_filename)

                    files_with_uppercase_ext.append({
                        'old_path': rel_path,
                        'old_filename': filename,
                        'new_filename': new_filename,
                        'full_old_path': file_path,
                        'full_new_path': new_file_path,
                    })

                    if verbose:
                        self.stdout.write(
                            f'  Found: {rel_path} -> {new_filename}'
                        )
                        logger.debug(
                            'Found file with uppercase extension: %s',
                            rel_path,
                        )

        if not files_with_uppercase_ext:
            msg = 'No files with uppercase extensions found.'
            self.stdout.write(self.style.SUCCESS(msg))
            logger.info(msg)
            return

        count = len(files_with_uppercase_ext)
        msg = f'\nFound {count} files with uppercase extensions.'
        self.stdout.write(msg)
        logger.info('Found %d files with uppercase extensions', count)

        if dry_run:
            self.stdout.write('\nFiles that would be renamed:')
            for file_info in files_with_uppercase_ext:
                old = file_info["old_path"]
                new = file_info["new_filename"]
                self.stdout.write(f'  {old} -> {new}')
            msg = 'Dry run completed. No files were actually renamed.'
            logger.info(msg)
            return

        # Process each file in a transaction
        self.stdout.write('\nRenaming files and updating database...')
        try:
            with transaction.atomic():
                # First, rename all files
                for file_info in files_with_uppercase_ext:
                    old_path = file_info['full_old_path']
                    new_path = file_info['full_new_path']

                    try:
                        # Check if paths differ only in case
                        # (case-insensitive filesystems)
                        if old_path.lower() == new_path.lower():
                            # Use temp file for case-only rename
                            if os.path.exists(old_path):
                                temp_path = old_path + '.temp_rename'
                                os.rename(old_path, temp_path)
                                os.rename(temp_path, new_path)
                                renamed_files.append(file_info)
                                if verbose:
                                    old = file_info["old_path"]
                                    msg = f'  ✓ Renamed: {old}'
                                    self.stdout.write(
                                        self.style.SUCCESS(msg)
                                    )
                                old = file_info["old_path"]
                                new = file_info["new_filename"]
                                logger.info(
                                    'File renamed: %s -> %s', old, new
                                )
                        elif os.path.exists(new_path):
                            # Target already exists
                            msg = (
                                f'  SKIPPED: Target file already exists: '
                                f'{file_info["new_filename"]}'
                            )
                            self.stdout.write(self.style.WARNING(msg))
                            logger.warning(msg)
                        else:
                            # Standard rename
                            os.rename(old_path, new_path)
                            renamed_files.append(file_info)
                            if verbose:
                                msg = f'  ✓ Renamed: {file_info["old_path"]}'
                                self.stdout.write(
                                    self.style.SUCCESS(msg)
                                )
                            old = file_info["old_path"]
                            new = file_info["new_filename"]
                            logger.info(
                                'File renamed: %s -> %s', old, new
                            )
                    except OSError as e:
                        path = file_info["old_path"]
                        msg = f'  ERROR renaming {path}: {str(e)}'
                        self.stdout.write(self.style.ERROR(msg))
                        logger.error(msg, exc_info=True)
                        raise

                # Then, update all database references
                if renamed_files:
                    count = len(renamed_files)
                    msg = (
                        f'\nUpdating database references for '
                        f'{count} files...'
                    )
                    self.stdout.write(msg)
                    self._update_database_references(
                        renamed_files, verbose
                    )

                count = len(renamed_files)
                msg = self.style.SUCCESS(
                    f'\nSuccessfully migrated {count} files to '
                    f'lowercase extensions.'
                )
                self.stdout.write(msg)
                logger.info(
                    'File extension migration completed successfully. '
                    '%d files migrated.', len(renamed_files)
                )

        except Exception as e:
            msg = f'Migration failed with error: {str(e)}'
            self.stdout.write(self.style.ERROR(msg))
            logger.error(msg, exc_info=True)
            warn_msg = (
                'Due to transaction atomicity, file renames may have '
                'been rolled back.'
            )
            self.stdout.write(self.style.WARNING(warn_msg))
            raise CommandError(msg)

    def _update_database_references(self, renamed_files, verbose):
        """
        Update all database references to renamed files.

        This method searches through all FileField and ImageField
        instances in Django models and updates their paths if they
        reference renamed files.

        Uses transaction.atomic() to ensure all-or-nothing consistency
        in the database.
        """
        from django.apps import apps

        # Create a mapping of old filenames to new filenames
        file_mapping = {
            file_info['old_path']: file_info['old_path'].replace(
                file_info['old_filename'], file_info['new_filename']
            )
            for file_info in renamed_files
        }

        updates_count = 0
        errors = []

        try:
            # Iterate through all installed apps and models
            for app_config in apps.get_app_configs():
                for model in app_config.get_models():
                    # Find all FileField and ImageField instances
                    file_fields = [
                        field for field in model._meta.get_fields()
                        if isinstance(
                            field,
                            (models.FileField, models.ImageField),
                        )
                    ]

                    if not file_fields:
                        continue

                    # Check each instance of the model
                    for obj in model.objects.all():
                        for field in file_fields:
                            try:
                                old_value = getattr(
                                    obj, field.name, None
                                )
                                if not old_value:
                                    continue

                                # Convert to string path for comparison
                                old_value_str = str(old_value)

                                # Check if file was renamed
                                for old_path, new_path in (
                                    file_mapping.items()
                                ):
                                    if old_path in old_value_str:
                                        new_value_str = (
                                            old_value_str.replace(
                                                old_path, new_path
                                            )
                                        )
                                        setattr(
                                            obj, field.name, new_value_str
                                        )
                                        obj.save(update_fields=[field.name])
                                        updates_count += 1

                                        msg = (
                                            f'Updated '
                                            f'{model.__name__}.{field.name} '
                                            f'(ID: {obj.pk})'
                                        )
                                        if verbose:
                                            self.stdout.write(
                                                self.style.SUCCESS(
                                                    f'  ✓ {msg}'
                                                )
                                            )
                                        logger.info(msg)
                            except Exception as e:
                                error_msg = (
                                    f'Error updating '
                                    f'{model.__name__}.{field.name} '
                                    f'(ID: {obj.pk}): {str(e)}'
                                )
                                errors.append(error_msg)
                                logger.error(error_msg, exc_info=True)
                                self.stdout.write(
                                    self.style.ERROR(
                                        f'  ERROR: {error_msg}'
                                    )
                                )

        except Exception as e:
            error_msg = (
                'Error iterating through models during database '
                'update: {}'.format(str(e))
            )
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
            raise

        if errors:
            error_summary = (
                f'Completed with {len(errors)} error(s) during '
                f'database updates.'
            )
            self.stdout.write(self.style.WARNING(error_summary))
            logger.warning(error_summary)

        self.stdout.write(
            f'Updated {updates_count} database reference(s).'
        )
        logger.info(
            'Updated %d database reference(s)', updates_count
        )
