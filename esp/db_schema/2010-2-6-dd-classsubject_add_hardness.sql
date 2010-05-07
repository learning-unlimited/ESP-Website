-- Add a string for the hardness rating of each class
ALTER TABLE program_class ADD hardness_rating varchar(64);
update program_class set hardness_rating='Normal';

