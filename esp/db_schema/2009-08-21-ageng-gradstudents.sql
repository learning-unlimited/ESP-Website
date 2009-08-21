-- Update users_teacherinfo to handle grad students' profiles.

-- Translate input: "G" --> 1, non-integers --> 0
UPDATE users_teacherinfo SET graduation_year='1' WHERE trim(graduation_year) = 'G';
UPDATE users_teacherinfo SET graduation_year='0' WHERE trim(graduation_year) NOT SIMILAR TO '[0-9]+';
-- Migrate data
ALTER TABLE users_teacherinfo ADD COLUMN graduation_year_int INTEGER;
UPDATE users_teacherinfo SET graduation_year_int = CAST( graduation_year AS INTEGER );
UPDATE users_teacherinfo SET graduation_year_int = 0 WHERE graduation_year_int IS NULL;
-- Clean up
ALTER TABLE users_teacherinfo ALTER COLUMN graduation_year_int SET NOT NULL;
ALTER TABLE users_teacherinfo DROP COLUMN graduation_year;
