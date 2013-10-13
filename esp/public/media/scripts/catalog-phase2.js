var dirty = false;

$j(document).ready(function() {
    $j("#catalog-sticky .pri-select").select2();
    $j("#catalog-sticky .pri-select").change(function() {
	dirty = true;
    });
});

$j(window).on('beforeunload', function() {
    if (dirty) {
	return ('Warning: You have unsaved changes. Please click save and ' +
		'exit if you wish to preserve your changes.')
    }
});

var error_and_quit = function(err) {
    //alert('Error: ' + err + '. Please report the issue to esp-web@mit.edu ' +
    //'if it is recurring.');
    //window.location = '/learn/' + program_core_url + 'studentreg_2';
};

save_and_redirect = function() {
    if (dirty) {
	priorities = {}
	$j("#catalog-sticky .pri-select").each(function() {
	    priorities[$j(this).data('pri')] = $j(this).val();
	});
	response = {};
	response[timeslot_id] = priorities;
	$j.ajax({
	    type: 'POST',
	    url: '/learn/' + program_core_url + 'save_priorities',
	    data: {
		'json_data': JSON.stringify(response),
		'csrfmiddlewaretoken': csrf_token(),
	    },
	    dataType: 'json',
	    async: false,
	    error: function(jqxhr, status, error) {
		error_and_quit(status + ":" + error)
	    },
	    success: function() {
		dirty = false;
	    }
	});
    }
};