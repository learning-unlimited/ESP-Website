CREATE TABLE "users_useravailability" (
    "id" serial NOT NULL PRIMARY KEY,
    "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    "event_id" integer NOT NULL REFERENCES "cal_event" ("id") DEFERRABLE INITIALLY DEFERRED,
    "role_id" integer NOT NULL REFERENCES "datatree_datatree" ("id") DEFERRABLE INITIALLY DEFERRED,
    "priority" numeric(3, 2) NOT NULL
);
