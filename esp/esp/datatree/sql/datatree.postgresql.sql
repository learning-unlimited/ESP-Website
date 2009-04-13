-- This file is part of the ESP Web Site
-- Copyright (c) Michael Axiak 2008
--
-- The ESP Web Site is free software; you can redistribute it and/or
-- modify it under the terms of the GNU General Public License
-- as published by the Free Software Foundation; either version 2
-- of the License, or (at your option) any later version.
--
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.
--
-- You should have received a copy of the GNU General Public License
-- along with this program; if not, write to the Free Software
-- Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
--
-- Contact Us:
-- ESP Web Group
-- MIT Educational Studies Program,
-- 84 Massachusetts Ave W20-467, Cambridge, MA 02139
-- Phone: 617-253-4882
-- Email: web@esp.mit.edu


-- ***
-- Table indices for the DataTree table
-- ***

-- Indices to facilitate range queries
CREATE INDEX datatree__rangestart ON datatree_datatree USING btree (rangestart);
CREATE INDEX datatree__rangeend ON datatree_datatree USING btree (rangeend);

-- Speeds up get_by_uri queries
CREATE INDEX datatree_uri ON datatree_datatree USING btree (uri) WHERE uri_correct = true;

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


-- ***
-- ESP plpgpsql functions
-- ***
-- Written by Mike Axiak.



-- Warning: Only pgsql superusers can create 'C'-based languages.
-- Commenting out the following inserts as a result.
-- To use them, either enable them or use the Postgres "createlang" command
-- to add the plpgsql language manually.

-- Function: plpgsql_call_handler()

-- DROP FUNCTION plpgsql_call_handler();

--CREATE OR REPLACE FUNCTION plpgsql_call_handler()
--  RETURNS language_handler AS
--'$libdir/plpgsql', 'plpgsql_call_handler'
--  LANGUAGE 'c' VOLATILE;
--ALTER FUNCTION plpgsql_call_handler() OWNER TO postgres;

-- Function: plpgsql_validator(oid)

-- DROP FUNCTION plpgsql_validator(oid);

--CREATE OR REPLACE FUNCTION plpgsql_validator(oid)
--  RETURNS void AS
--'$libdir/plpgsql', 'plpgsql_validator'
--  LANGUAGE 'c' VOLATILE;
--ALTER FUNCTION plpgsql_validator(oid) OWNER TO postgres;


-- Language: plpgsql

--CREATE LANGUAGE 'plpgsql' HANDLER plpgsql_call_handler
--                          LANCOMPILER 'PL/pgSQL';


-- Function: class__get_enrolled(integer, integer)

-- DROP FUNCTION class__get_enrolled(integer, integer);

CREATE OR REPLACE FUNCTION class__get_enrolled(user_id integer, program_id integer)
  RETURNS SETOF program_class AS
$BODY$DECLARE
   verb_confirm_rec RECORD;
   verb_prelim_rec RECORD;
   program_anchor_rec RECORD;
   output RECORD;
BEGIN
    -- Select confirm bit
    SELECT INTO verb_confirm_rec id, rangestart, rangeend FROM datatree_datatree WHERE uri = 'V/Flags/Registration/Confirmed';

    -- Select preliminary bit
    SELECT INTO verb_prelim_rec id, rangestart, rangeend FROM datatree_datatree WHERE uri = 'V/Flags/Registration/Preliminary';

    -- get the program anchor node
    SELECT INTO program_anchor_rec "datatree_datatree".id, rangestart, rangeend FROM "datatree_datatree"
      INNER JOIN "program_program" ON "program_program"."anchor_id" = "datatree_datatree"."id"
      WHERE "program_program"."id" = program_id LIMIT 1;

    FOR output IN
    SELECT DISTINCT
    program_class.*
    FROM  "program_class"

    INNER JOIN "datatree_datatree" AS "program_class__anchor"
        ON "program_class"."anchor_id" = "program_class__anchor"."id"

    LEFT OUTER JOIN "users_userbit"
      ON "program_class__anchor"."id" = "users_userbit"."qsc_id"

    INNER JOIN "datatree_datatree" as "users_userbit__qsc"
      ON "users_userbit"."qsc_id" = "users_userbit__qsc"."id"

    INNER JOIN "datatree_datatree" AS "users_userbit__verb"
      ON "users_userbit"."verb_id" = "users_userbit__verb"."id"

    WHERE
    (
      ("program_class__anchor".rangestart >= program_anchor_rec.rangestart AND
       "program_class__anchor".rangeend   <= program_anchor_rec.rangeend)
      AND
      ("users_userbit"."user_id" IS NULL OR "users_userbit"."user_id" = user_id)
      AND
      ("users_userbit"."startdate" <= now())
      AND
      ("users_userbit"."enddate" >= now())
      AND
      (
        ("users_userbit"."recursive" = True AND
         "users_userbit__qsc"."rangestart" <= "program_class__anchor"."rangestart" AND
         "users_userbit__qsc"."rangeend" >= "program_class__anchor"."rangeend"
        )
        OR
        "users_userbit"."qsc_id" = "program_class__anchor"."id"
      )
      AND
      (
        (
          ("users_userbit"."recursive" = True AND
           "users_userbit__verb"."rangestart" <= verb_confirm_rec.rangestart AND
           "users_userbit__verb"."rangeend" >= verb_confirm_rec.rangeend
          )
          OR
          "users_userbit"."verb_id" = 180
        )
        OR
        (
          ("users_userbit"."recursive" = True AND
           "users_userbit__verb"."rangestart" <= verb_prelim_rec.rangestart AND
           "users_userbit__verb"."rangeend" >= verb_prelim_rec.rangeend
          )
          OR
          "users_userbit"."verb_id" = 179
        )
      )
    ) LOOP
    return next output;
    END LOOP;
END;$BODY$
  LANGUAGE 'plpgsql' STABLE;


-- Function: userbit__bits_get_qsc(integer, integer, timestamp with time zone, timestamp with time zone)

-- DROP FUNCTION userbit__bits_get_qsc(integer, integer, timestamp with time zone, timestamp with time zone);

CREATE OR REPLACE FUNCTION userbit__bits_get_qsc(user_id integer, verb_id integer, start_ts timestamp with time zone, end_ts timestamp with time zone)
  RETURNS SETOF users_userbit AS
$BODY$DECLARE
   verb_rec RECORD;
   output RECORD;
BEGIN
    -- Select verb
    SELECT INTO verb_rec rangestart, rangeend FROM datatree_datatree WHERE id = verb_id;

    FOR output IN
    SELECT DISTINCT
    "users_userbit"."id","users_userbit"."user_id","users_userbit"."qsc_id",
    "users_userbit"."verb_id","users_userbit"."startdate","users_userbit"."enddate","users_userbit"."recursive"

    FROM "users_userbit"

    INNER JOIN "datatree_datatree" AS "users_userbit__verb"
        ON "users_userbit"."verb_id" = "users_userbit__verb"."id"

    WHERE

    (
      (
        ("users_userbit"."user_id" IS NULL OR "users_userbit"."user_id" = user_id)
        AND
        ("users_userbit"."startdate" <= start_ts)
        AND
        ("users_userbit"."enddate" >= end_ts)
        AND
        (
          ("users_userbit"."recursive" = True AND
           "users_userbit__verb"."rangestart" <= verb_rec.rangestart AND
           "users_userbit__verb"."rangeend" >= verb_rec.rangeend
          )
          OR
          "users_userbit"."verb_id" = verb_id
        )
      )
    ) LOOP
    return next output;
    END LOOP;
END;$BODY$
  LANGUAGE 'plpgsql' STABLE;

-- Function: userbit__bits_get_qsc_root(integer, integer, timestamp with time zone, timestamp with time zone, integer)

-- DROP FUNCTION userbit__bits_get_qsc_root(integer, integer, timestamp with time zone, timestamp with time zone, integer);

CREATE OR REPLACE FUNCTION userbit__bits_get_qsc_root(user_id integer, verb_id integer, start_ts timestamp with time zone, end_ts timestamp with time zone, qscroot_id integer)
  RETURNS SETOF users_userbit AS
$BODY$DECLARE
   verb_rec RECORD;
   qscroot_rec RECORD;
   output RECORD;
BEGIN
    -- Select verb
    SELECT INTO verb_rec rangestart, rangeend FROM datatree_datatree WHERE id = verb_id;

    -- Select qsc root
    SELECT INTO qscroot_rec rangestart, rangeend FROM datatree_datatree WHERE id = qscroot_id;

    FOR output IN
    SELECT DISTINCT
    "users_userbit"."id","users_userbit"."user_id","users_userbit"."qsc_id",
    "users_userbit"."verb_id","users_userbit"."startdate","users_userbit"."enddate","users_userbit"."recursive"

    FROM "users_userbit"

    INNER JOIN "datatree_datatree" AS "users_userbit__verb"
        ON "users_userbit"."verb_id" = "users_userbit__verb"."id"

    INNER JOIN "datatree_datatree" AS "users_userbit__qsc"
        ON "users_userbit"."qsc_id" = "users_userbit__qsc"."id"

    WHERE

    (
      (
        ("users_userbit"."user_id" IS NULL OR "users_userbit"."user_id" = user_id)
        AND
        ("users_userbit"."startdate" IS NULL OR "users_userbit"."startdate" <= start_ts)
        AND
        ("users_userbit"."enddate" >= end_ts)
        AND
        (
          ("users_userbit"."recursive" = True AND
           "users_userbit__verb"."rangestart" <= verb_rec.rangestart AND
           "users_userbit__verb"."rangeend" >= verb_rec.rangeend
          )
          OR
          "users_userbit"."verb_id" = verb_id
        )
        AND
        (
          ("users_userbit__qsc"."rangestart" >= qscroot_rec.rangestart AND
           "users_userbit__qsc"."rangeend" <= qscroot_rec.rangeend
          )
          OR
          "users_userbit"."qsc_id" = qscroot_id
        )
      )
    ) LOOP
    return next output;
    END LOOP;
END;$BODY$
  LANGUAGE 'plpgsql' STABLE;

-- Function: userbit__bits_get_user(integer, integer, timestamp with time zone, timestamp with time zone)

-- DROP FUNCTION userbit__bits_get_user(integer, integer, timestamp with time zone, timestamp with time zone);

CREATE OR REPLACE FUNCTION userbit__bits_get_user(qsc_id integer, verb_id integer, start_ts timestamp with time zone, end_ts timestamp with time zone)
  RETURNS SETOF users_userbit AS
$BODY$DECLARE
    verb_rec RECORD;
    qsc_rec RECORD;
    output RECORD;
BEGIN
    -- Select verb
    SELECT INTO verb_rec rangestart, rangeend FROM datatree_datatree WHERE id = verb_id;

    -- Select qsc
    SELECT INTO qsc_rec rangestart, rangeend FROM datatree_datatree WHERE id = qsc_id;

    FOR output IN
    SELECT DISTINCT
    "users_userbit"."id","users_userbit"."user_id","users_userbit"."qsc_id","users_userbit"."verb_id",
    "users_userbit"."startdate","users_userbit"."enddate","users_userbit"."recursive"

    FROM "users_userbit"

    INNER JOIN "datatree_datatree" AS "users_userbit__verb"
      ON "users_userbit"."verb_id" = "users_userbit__verb"."id"

    INNER JOIN "datatree_datatree" AS "users_userbit__qsc"
      ON "users_userbit"."qsc_id" = "users_userbit__qsc"."id"

    WHERE
    (
      (
        ("users_userbit"."startdate" <= start_ts)
        AND
        ("users_userbit"."enddate" >= end_ts)
      )
      AND
      (
        ("users_userbit__verb"."rangestart" <= verb_rec.rangestart AND
         "users_userbit__verb"."rangeend" >= verb_rec.rangeend AND
         "users_userbit__qsc"."rangeend" >= qsc_rec.rangeend AND
         "users_userbit__qsc"."rangestart" <= qsc_rec.rangestart AND
         "users_userbit"."recursive" = True)
        OR
        ("users_userbit"."verb_id" = verb_id AND "users_userbit"."qsc_id" = qsc_id)
      )
    ) LOOP
    RETURN NEXT output;
    END LOOP;
END;$BODY$
  LANGUAGE 'plpgsql' STABLE;

-- Function: userbit__bits_get_user_real(integer, integer, timestamp with time zone, timestamp with time zone)

-- DROP FUNCTION userbit__bits_get_user_real(integer, integer, timestamp with time zone, timestamp with time zone);

CREATE OR REPLACE FUNCTION userbit__bits_get_user_real(qsc_id integer, verb_id integer, start_ts timestamp with time zone, end_ts timestamp with time zone)
  RETURNS SETOF auth_user AS
$BODY$DECLARE
    verb_rec RECORD;
    qsc_rec RECORD;
    output RECORD;
BEGIN
    -- Select verb
    SELECT INTO verb_rec rangestart, rangeend FROM datatree_datatree WHERE id = verb_id;

    -- Select qsc
    SELECT INTO qsc_rec rangestart, rangeend FROM datatree_datatree WHERE id = qsc_id;

    FOR output IN
    SELECT DISTINCT
    "auth_user"."id","auth_user"."username","auth_user"."first_name","auth_user"."last_name",
    "auth_user"."email","auth_user"."password","auth_user"."is_staff","auth_user"."is_active",
    "auth_user"."is_superuser","auth_user"."last_login","auth_user"."date_joined"

    FROM "auth_user"

    INNER JOIN "users_userbit" AS "users_userbit"
      ON "auth_user"."id" = "users_userbit"."user_id"

    INNER JOIN "datatree_datatree" AS "users_userbit__verb"
      ON "users_userbit"."verb_id" = "users_userbit__verb"."id"

    INNER JOIN "datatree_datatree" AS "users_userbit__qsc"
      ON "users_userbit"."qsc_id" = "users_userbit__qsc"."id"

    WHERE
    (
      (
        ("users_userbit"."startdate" <= start_ts)
        AND
        ("users_userbit"."enddate" >= end_ts)
      )
      AND
      (
        ("users_userbit__verb"."rangestart" <= verb_rec.rangestart AND
         "users_userbit__verb"."rangeend" >= verb_rec.rangeend AND
         "users_userbit__qsc"."rangeend" >= qsc_rec.rangeend AND
         "users_userbit__qsc"."rangestart" <= qsc_rec.rangestart AND
         "users_userbit"."recursive" = True)
        OR
        ("users_userbit"."verb_id" = verb_id AND "users_userbit"."qsc_id" = qsc_id)
      )
    ) LOOP
    RETURN NEXT output;
    END LOOP;
END;$BODY$
  LANGUAGE 'plpgsql' STABLE;

-- Function: userbit__bits_get_verb(integer, integer, timestamp with time zone, timestamp with time zone)

-- DROP FUNCTION userbit__bits_get_verb(integer, integer, timestamp with time zone, timestamp with time zone);

CREATE OR REPLACE FUNCTION userbit__bits_get_verb(user_id integer, qsc_id integer, start_ts timestamp with time zone, end_ts timestamp with time zone)
  RETURNS SETOF users_userbit AS
$BODY$DECLARE
   qsc_rec RECORD;
   output RECORD;
BEGIN
    -- Select qsc
    SELECT INTO qsc_rec rangestart, rangeend FROM datatree_datatree WHERE id = qsc_id;

    FOR output IN
    SELECT DISTINCT
    "users_userbit"."id","users_userbit"."user_id","users_userbit"."qsc_id",
    "users_userbit"."verb_id","users_userbit"."startdate","users_userbit"."enddate","users_userbit"."recursive"

    FROM "users_userbit"

    INNER JOIN "datatree_datatree" AS "users_userbit__qsc"
        ON "users_userbit"."qsc_id" = "users_userbit__qsc"."id"

    WHERE

    (
      (
        ("users_userbit"."user_id" IS NULL OR "users_userbit"."user_id" = user_id)
        AND
        ("users_userbit"."startdate" <= start_ts)
        AND
        ("users_userbit"."enddate" >= end_ts)
        AND
        (
          ("users_userbit"."recursive" = True AND
           "users_userbit__qsc"."rangestart" <= qsc_rec.rangestart AND
           "users_userbit__qsc"."rangeend" >= qsc_rec.rangeend
          )
          OR
          "users_userbit"."qsc_id" = qsc_id
        )
      )
    ) LOOP
    return next output;
    END LOOP;
END;$BODY$
  LANGUAGE 'plpgsql' STABLE;

-- Function: userbit__bits_get_verb_root(integer, integer, timestamp with time zone, timestamp with time zone, integer)

-- DROP FUNCTION userbit__bits_get_verb_root(integer, integer, timestamp with time zone, timestamp with time zone, integer);

CREATE OR REPLACE FUNCTION userbit__bits_get_verb_root(user_id integer, qsc_id integer, start_ts timestamp with time zone, end_ts timestamp with time zone, verbroot_id integer)
  RETURNS SETOF users_userbit AS
$BODY$DECLARE
   qsc_rec RECORD;
   output RECORD;
BEGIN
    -- Select qsc
    SELECT INTO qsc_rec rangestart, rangeend FROM datatree_datatree WHERE id = qsc_id;

    FOR output IN
    SELECT DISTINCT
    "users_userbit"."id","users_userbit"."user_id","users_userbit"."qsc_id",
    "users_userbit"."verb_id","users_userbit"."startdate","users_userbit"."enddate","users_userbit"."recursive"

    FROM "users_userbit"

    INNER JOIN "datatree_datatree" AS "users_userbit__qsc"
        ON "users_userbit"."qsc_id" = "users_userbit__qsc"."id"

    WHERE

    (
      (
        ("users_userbit"."user_id" IS NULL OR "users_userbit"."user_id" = user_id)
        AND
        ("users_userbit"."startdate" <= start_ts)
        AND
        ("users_userbit"."enddate" >= end_ts)
        AND
        (
          ("users_userbit"."recursive" = True AND
           "users_userbit__qsc"."rangestart" <= qsc_rec.rangestart AND
           "users_userbit__qsc"."rangeend" >= qsc_rec.rangeend
          )
          OR
          "users_userbit"."qsc_id" = qsc_id
        )
      )
    ) LOOP
    return next output;
    END LOOP;
END;$BODY$
  LANGUAGE 'plpgsql' STABLE;

-- Function: userbit__user_has_perms(integer, integer, integer, timestamp with time zone, boolean)

-- DROP FUNCTION userbit__user_has_perms(integer, integer, integer, timestamp with time zone, boolean);

CREATE OR REPLACE FUNCTION userbit__user_has_perms(user_id integer, qsc_id integer, verb_id integer, now_ts timestamp with time zone, recursive_required boolean)
  RETURNS boolean AS
$BODY$DECLARE
   qsc_rec RECORD;
   verb_rec RECORD;
   userbit_id RECORD;
BEGIN
    IF recursive_required THEN
        -- Now we have to use verb recursion
        -- Select qsc
        SELECT INTO qsc_rec rangestart, rangeend FROM datatree_datatree WHERE id = qsc_id;

        -- Select verb
        SELECT INTO verb_rec rangestart, rangeend FROM datatree_datatree WHERE id = verb_id;

        SELECT INTO userbit_id "users_userbit"."id" FROM "users_userbit"

        INNER JOIN "datatree_datatree" AS "users_userbit__verb"
          ON "users_userbit"."verb_id" = "users_userbit__verb"."id"

        INNER JOIN "datatree_datatree" AS "users_userbit__qsc"
          ON "users_userbit"."qsc_id" = "users_userbit__qsc"."id"
        WHERE
        (
          (
             ("users_userbit"."user_id" IS NULL OR "users_userbit"."user_id" = user_id)
             AND
             (
               ("users_userbit"."startdate" <= now_ts)
               AND
               ("users_userbit"."enddate" > now_ts)
             )
          )
          AND
            ("users_userbit__verb"."rangestart" <= verb_rec.rangestart AND
             "users_userbit__verb"."rangeend" >= verb_rec.rangeend AND
             "users_userbit"."verb_id" = "users_userbit__verb"."id" AND
             "users_userbit__qsc"."rangeend" >= qsc_rec.rangeend AND
             "users_userbit__qsc"."rangestart" <= qsc_rec.rangestart AND
             "users_userbit"."qsc_id" = "users_userbit__qsc"."id" AND
             "users_userbit"."recursive" = True
           )
        )
        LIMIT 1;

        IF NOT FOUND THEN
            RETURN false;
        ELSE
            RETURN true;
        END IF;
    ELSE
        -- The simple case first...no recursion.
        SELECT INTO userbit_id "users_userbit"."id" FROM "users_userbit"
        WHERE
        (
          (
             ("users_userbit"."user_id" IS NULL OR "users_userbit"."user_id" = user_id)
             AND
             (
               ("users_userbit"."startdate" <= now_ts)
               AND
               ("users_userbit"."enddate" > now_ts)
             )
          )
          AND
            ("users_userbit"."verb_id" = verb_id AND "users_userbit"."qsc_id" = qsc_id)
        )
        LIMIT 1;

        IF NOT FOUND THEN
            -- Now we have to use verb recursion
            -- Select qsc
            SELECT INTO qsc_rec rangestart, rangeend FROM datatree_datatree WHERE id = qsc_id;

            -- Select verb
            SELECT INTO verb_rec rangestart, rangeend FROM datatree_datatree WHERE id = verb_id;

            SELECT INTO userbit_id "users_userbit"."id" FROM "users_userbit"

            INNER JOIN "datatree_datatree" AS "users_userbit__verb"
              ON "users_userbit"."verb_id" = "users_userbit__verb"."id"

            INNER JOIN "datatree_datatree" AS "users_userbit__qsc"
              ON "users_userbit"."qsc_id" = "users_userbit__qsc"."id"
            WHERE
            (
              (
                 ("users_userbit"."user_id" IS NULL OR "users_userbit"."user_id" = user_id)
                 AND
                 (
                   ("users_userbit"."startdate" <= now_ts)
                   AND
                   ("users_userbit"."enddate" > now_ts)
                 )
              )
              AND
                ("users_userbit__verb"."rangestart" <= verb_rec.rangestart AND
                 "users_userbit__verb"."rangeend" >= verb_rec.rangeend AND
                 "users_userbit"."verb_id" = "users_userbit__verb"."id" AND
                 "users_userbit__qsc"."rangeend" >= qsc_rec.rangeend AND
                 "users_userbit__qsc"."rangestart" <= qsc_rec.rangestart AND
                 "users_userbit"."qsc_id" = "users_userbit__qsc"."id" AND
                 "users_userbit"."recursive" = True
                )
            )
            LIMIT 1;

            IF NOT FOUND THEN
                RETURN false;
            ELSE
                RETURN true;
            END IF;
        ELSE
            RETURN true;
        END IF;
    END IF;
END;$BODY$
  LANGUAGE 'plpgsql' STABLE;
