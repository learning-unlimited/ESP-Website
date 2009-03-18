BEGIN;

-- Creating nav bar categories

DROP TABLE IF EXISTS "web_navbarcategory";

CREATE TABLE "web_navbarcategory" (
    "id" serial NOT NULL PRIMARY KEY,
    "anchor_id" integer NULL REFERENCES "datatree_datatree" ("id"),
    "include_auto_links" boolean NOT NULL,
    "name" varchar(64) NOT NULL,
    "long_explanation" text NOT NULL);
    
-- Populating initial nav bar categories

INSERT INTO web_navbarcategory (name, include_auto_links, id, anchor_id, long_explanation) VALUES ('default', 'f', 1, NULL, 'The default category that new nav bars and QSD pages get assigned to.');
INSERT INTO web_navbarcategory (name, include_auto_links, id, anchor_id, long_explanation) VALUES ('learn', 'f', 2, NULL, 'Default category for "Take a class" pages.');
INSERT INTO web_navbarcategory (name, include_auto_links, id, anchor_id, long_explanation) VALUES ('teach', 'f', 3, NULL, 'Default category for "Teach a class" pages.');
INSERT INTO web_navbarcategory (name, include_auto_links, id, anchor_id, long_explanation) VALUES ('about', 'f', 4, NULL, 'Default category for "Discover ESP" pages.');
INSERT INTO web_navbarcategory (name, include_auto_links, id, anchor_id, long_explanation) VALUES ('splash', 't', 5, 36, 'For Splash specific pages.');
INSERT INTO web_navbarcategory (name, include_auto_links, id, anchor_id, long_explanation) VALUES ('hssp', 't', 6, 38, 'For HSSP specific pages.');
INSERT INTO web_navbarcategory (name, include_auto_links, id, anchor_id, long_explanation) VALUES ('internal', 'f', 7, NULL, 'MyESP and contact pages.');
INSERT INTO web_navbarcategory (name, include_auto_links, id, anchor_id, long_explanation) VALUES ('involved', 'f', 8, NULL, 'Get Involved pages.');
INSERT INTO web_navbarcategory (name, include_auto_links, id, anchor_id, long_explanation) VALUES ('resources', 'f', 9, NULL, 'Resource/archive pages.');
    
COMMIT;

    
BEGIN;

-- Updating nav bar entries

ALTER TABLE "web_navbarentry" ALTER COLUMN "path_id" DROP NOT NULL;
ALTER TABLE "web_navbarentry" ADD COLUMN "category_id" integer NULL REFERENCES "web_navbarcategory" ("id");
UPDATE "web_navbarentry" SET "category_id" = (SELECT T1."id" FROM "web_navbarcategory" T1 LEFT JOIN "web_navbarentry" T2 ON T1."name" = T2."section" WHERE "web_navbarentry"."id" = T2.id LIMIT 1) WHERE char_length("section") > 1;
UPDATE "web_navbarentry" SET "category_id" = 1 WHERE "category_id" IS NULL;
ALTER TABLE "web_navbarentry" ALTER COLUMN "category_id" SET NOT NULL;
ALTER TABLE "web_navbarentry" DROP COLUMN "section";

-- Updating QSD to use nav categories

ALTER TABLE "qsd_quasistaticdata" ADD COLUMN "nav_category_id" integer NULL REFERENCES "web_navbarcategory" ("id");
UPDATE "qsd_quasistaticdata" SET "nav_category_id" = (SELECT T1.id FROM web_navbarcategory T1 INNER JOIN qsd_quasistaticdata T2 ON (T1.name = (SELECT substring(T2.name from '^(.*):'))) AND T2.id = "qsd_quasistaticdata"."id");
UPDATE "qsd_quasistaticdata" SET "nav_category_id" = 1 WHERE "nav_category_id" IS NULL;
ALTER TABLE "qsd_quasistaticdata" ALTER COLUMN "nav_category_id" SET NOT NULL;

COMMIT;
