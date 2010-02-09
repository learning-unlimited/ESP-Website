UPDATE program_programmodule SET aux_calls = aux_calls || ',ajax_requests,ajax_restypes' WHERE handler = 'TeacherClassRegModule' AND aux_calls NOT LIKE '%,ajax_requests,ajax_restypes%';
