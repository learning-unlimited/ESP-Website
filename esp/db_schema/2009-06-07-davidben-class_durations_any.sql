-- Drop column from modules_classregmoduleinfo
-- This field hasn't been used for years

BEGIN;

ALTER TABLE modules_classregmoduleinfo DROP COLUMN class_durations_any;

COMMIT;
