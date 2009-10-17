UPDATE program_programmodule SET aux_calls = aux_calls || ',ajax_schedule_assignments,ajax_schedule_class,ajax_schedule_last_changed' WHERE main_call = 'ajax_scheduling' AND module_type = 'manage' AND aux_calls NOT LIKE '%ajax_schedule_assignments,ajax_schedule_class,ajax_schedule_last_changed%';

