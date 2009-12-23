CREATE TABLE "shortterm_volunteerregistration" (
    "id" serial NOT NULL PRIMARY KEY,
    "your_name" varchar(100) NOT NULL,
    "email_address" varchar(75) NOT NULL,
    "phone_number" varchar(32) NOT NULL,
    "availability" varchar(255) NOT NULL,
    "notes" text NOT NULL
);
