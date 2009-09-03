-- Add category column to miniblog announcements
ALTER TABLE miniblog_announcementlink ADD COLUMN category character varying(32);
