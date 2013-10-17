var dirty = false;

$j(document).ready(function() {
    $j('#catalog-sticky .pri-select').select2();
    for (var i = 0; i < num_priorities; ++i) {
        catalog_view_model.prioritySelection[i].subscribe(function() {
            dirty = true;
        });
    }
});

$j(window).on('beforeunload', function() {
    if (dirty) {
        return ('Warning: You have unsaved changes. Please click save and ' +
                'exit if you wish to preserve your changes.')
    }
});

var error_and_quit = function(err) {
    alert('Error: ' + err + '. Please report the issue to esp-web@mit.edu ' +
          'if it is recurring.');
    window.location = '/learn/' + program_core_url + 'studentreg_2';
};

build_json_data = function(form) {
    var $form = $j(form);
    var learn_url = program_base_url.replace(/^\/json/, '/learn');
    if (dirty) {
        var priorities = {};
        $j('#catalog-sticky .pri-select').each(function() {
            priorities[$j(this).data('pri')] = $j(this).val();
        });
        var response = {};
        response[timeslot_id] = priorities;
        var json_data = JSON.stringify(response);
        $form.find("input[name=json_data]").val(json_data);
        $form.attr('action', learn_url + 'save_priorities');
        $form.attr('method', 'post');
    }
    else {
        $form.attr('action', learn_url + 'studentreg');
        $form.attr('method', 'get');
    }
    return true;
};
