-- Add columns in module_classregmoduleinfo
-- This helps to make the teacher class reg form smarter and more flexible.

BEGIN;

ALTER TABLE modules_classregmoduleinfo ADD COLUMN allowed_sections character varying(100);
ALTER TABLE modules_classregmoduleinfo ALTER COLUMN allowed_sections SET STORAGE EXTENDED;
UPDATE modules_classregmoduleinfo SET allowed_sections = '';
ALTER TABLE modules_classregmoduleinfo ALTER COLUMN allowed_sections SET NOT NULL;

ALTER TABLE modules_classregmoduleinfo ADD COLUMN ask_for_room boolean;
ALTER TABLE modules_classregmoduleinfo ALTER COLUMN ask_for_room SET STORAGE PLAIN;
UPDATE modules_classregmoduleinfo SET ask_for_room = false;
ALTER TABLE modules_classregmoduleinfo ALTER COLUMN ask_for_room SET NOT NULL;

COMMIT;
