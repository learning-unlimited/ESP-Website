ALTER TABLE resources_resourcerequest ADD COLUMN desired_value text;
ALTER TABLE resources_resourcetype ALTER COLUMN attributes_pickled DROP NOT NULL;
