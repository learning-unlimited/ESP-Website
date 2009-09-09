ALTER TABLE modules_classregmoduleinfo ADD COLUMN progress_mode integer NOT NULL DEFAULT 1;

ALTER TABLE modules_studentclassregmoduleinfo ADD COLUMN progress_mode integer NOT NULL DEFAULT 1;
ALTER TABLE modules_studentclassregmoduleinfo ADD COLUMN class_cap_multiplier numeric(3, 2) NOT NULL DEFAULT 1.0;
ALTER TABLE modules_studentclassregmoduleinfo ADD COLUMN class_cap_offset integer NOT NULL DEFAULT 0;
ALTER TABLE modules_studentclassregmoduleinfo ADD COLUMN confirm_button_text varchar(80) NOT NULL DEFAULT 'Confirm';
ALTER TABLE modules_studentclassregmoduleinfo ADD COLUMN view_button_text varchar(80) NOT NULL DEFAULT 'View Receipt';
ALTER TABLE modules_studentclassregmoduleinfo ADD COLUMN cancel_button_text varchar(80) NOT NULL DEFAULT 'Cancel Registration';
ALTER TABLE modules_studentclassregmoduleinfo ADD COLUMN cancel_button_dereg boolean NOT NULL DEFAULT FALSE;

ALTER TABLE modules_dbreceipt ADD COLUMN action varchar(80) NOT NULL DEFAULT 'confirm';
