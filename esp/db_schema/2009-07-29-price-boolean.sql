-- Create tables for Boolean expressions and schedule constraint models
-- Michael Price 7/29/2009

CREATE TABLE "program_booleantoken" (
    "id" serial NOT NULL PRIMARY KEY,
    "exp_id" integer NOT NULL,
    "text" text NOT NULL,
    "seq" integer NOT NULL
)
;
CREATE TABLE "program_booleanexpression" (
    "id" serial NOT NULL PRIMARY KEY,
    "label" varchar(80) NOT NULL
)
;
ALTER TABLE "program_booleantoken" ADD CONSTRAINT "exp_id_refs_id_237a1753" FOREIGN KEY ("exp_id") REFERENCES "program_booleanexpression" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE "program_scheduleconstraint" (
    "id" serial NOT NULL PRIMARY KEY,
    "program_id" integer NOT NULL REFERENCES "program_program" ("id") DEFERRABLE INITIALLY DEFERRED,
    "condition_id" integer NOT NULL REFERENCES "program_booleanexpression" ("id") DEFERRABLE INITIALLY DEFERRED,
    "requirement_id" integer NOT NULL REFERENCES "program_booleanexpression" ("id") DEFERRABLE INITIALLY DEFERRED
)
;
CREATE TABLE "program_scheduletesttimeblock" (
    "booleantoken_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "program_booleantoken" ("id") DEFERRABLE INITIALLY DEFERRED,
    "timeblock_id" integer NOT NULL REFERENCES "cal_event" ("id") DEFERRABLE INITIALLY DEFERRED
)
;
CREATE TABLE "program_scheduletestoccupied" (
    "scheduletesttimeblock_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "program_scheduletesttimeblock" ("booleantoken_ptr_id") DEFERRABLE INITIALLY DEFERRED
)
;
CREATE TABLE "program_scheduletestcategory" (
    "scheduletesttimeblock_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "program_scheduletesttimeblock" ("booleantoken_ptr_id") DEFERRABLE INITIALLY DEFERRED,
    "category_id" integer NOT NULL
)
;
CREATE TABLE "program_scheduletestsectionlist" (
    "scheduletesttimeblock_ptr_id" integer NOT NULL PRIMARY KEY REFERENCES "program_scheduletesttimeblock" ("booleantoken_ptr_id") DEFERRABLE INITIALLY DEFERRED,
    "section_ids" text NOT NULL
)
;

CREATE INDEX "program_booleantoken_exp_id" ON "program_booleantoken" ("exp_id");
CREATE INDEX "program_scheduleconstraint_program_id" ON "program_scheduleconstraint" ("program_id");
CREATE INDEX "program_scheduleconstraint_condition_id" ON "program_scheduleconstraint" ("condition_id");
CREATE INDEX "program_scheduleconstraint_requirement_id" ON "program_scheduleconstraint" ("requirement_id");
CREATE INDEX "program_scheduletesttimeblock_timeblock_id" ON "program_scheduletesttimeblock" ("timeblock_id");
CREATE INDEX "program_scheduletestcategory_category_id" ON "program_scheduletestcategory" ("category_id");

