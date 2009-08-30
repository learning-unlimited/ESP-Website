ALTER TABLE program_program ADD COLUMN program_allow_waitlist boolean DEFAULT false;
UPDATE program_programmodule SET aux_calls = aux_calls || ',waitlist_subscribe' WHERE handler = 'StudentRegCore';
