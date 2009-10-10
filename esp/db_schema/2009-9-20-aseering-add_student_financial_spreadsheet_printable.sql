UPDATE program_programmodule SET aux_calls = aux_calls || ',student_financial_spreadsheet' WHERE main_call = 'printoptions' AND module_type = 'manage' AND aux_calls NOT LIKE '%student_financial_spreadsheet%';

