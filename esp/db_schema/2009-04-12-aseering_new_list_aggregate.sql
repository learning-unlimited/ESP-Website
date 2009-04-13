--- ***
--- "List" aggregate
--- ***

CREATE OR REPLACE FUNCTION comma_cat (text, text)
  RETURNS text AS
  'SELECT CASE
    WHEN $2 is null or $2 = '''' THEN $1
    WHEN $1 is null or $1 = '''' THEN $2
    ELSE $1 || '','' || $2
  END'
LANGUAGE sql;

CREATE AGGREGATE list (
       BASETYPE = text, 
       SFUNC = comma_cat,
       STYPE = text,
       INITCOND = ''
);

