-- aseering 4/7/2009
-- In order to take full advantage of this change, you will also need to
-- re-run the SQL file "esp/esp/datatree/sql/datatree.postgresql.sql",
-- to update our plpgsql functions to not check for null-ness.

UPDATE users_userbit SET startdate='1000-01-01 00:00:00' WHERE startdate IS NULL;
UPDATE users_userbit SET enddate='9999-01-01 00:00:00' WHERE enddate IS NULL;
ALTER TABLE users_userbit ALTER startdate SET NOT NULL;
ALTER TABLE users_userbit ALTER enddate SET NOT NULL;
VACUUM FULL;
VACUUM ANALYZE;

-- Try to run the relevant SQL file automatically
\i '../esp/datatree/sql/datatree.postgresql.sql'