-- Add column distancefunc to ResourceType

BEGIN;

ALTER TABLE resources_resourcetype ADD COLUMN "distancefunc" text NULL;

COMMIT;
