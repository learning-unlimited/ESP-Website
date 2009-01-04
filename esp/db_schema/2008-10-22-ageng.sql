ALTER TABLE program_class ADD COLUMN requested_special_resources text;
ALTER TABLE program_class ALTER COLUMN requested_special_resources SET STORAGE EXTENDED;
ALTER TABLE program_class ADD COLUMN requested_room text;
ALTER TABLE program_class ALTER COLUMN requested_room SET STORAGE EXTENDED;
