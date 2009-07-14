-- Add registration status flag to class sections
-- so that directors can control whether how they behave
-- individually

BEGIN;

ALTER TABLE program_classsection ADD COLUMN registration_status INTEGER DEFAULT 0;

COMMIT;
