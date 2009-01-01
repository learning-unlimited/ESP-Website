#!/usr/bin/python

""" Database schema update script for PasswordRecoveryTicket. """

from django.db import transaction, connection

cursor = connection.cursor()

sql = """CREATE TABLE "users_passwordrecoveryticket" (
    "id" serial NOT NULL PRIMARY KEY,
    "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    "recover_key" varchar(30) NOT NULL,
    "expire" timestamp with time zone NULL
)"""

cursor.execute( sql )

