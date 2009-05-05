--- ***
--- "List" aggregate
--- ***

CREATE OR REPLACE FUNCTION comma_cat (text, integer)
  RETURNS text AS
  'SELECT CASE
    WHEN $2::text is null or $2::text = '''' THEN $1
    WHEN $1 is null or $1 = '''' THEN $2::text
    ELSE $1 || '','' || $2::text
  END'
LANGUAGE sql;

CREATE AGGREGATE list (
       BASETYPE = integer,
       SFUNC = comma_cat,
       STYPE = text,
       INITCOND = ''
);

