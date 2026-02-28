function setup_autocomplete()
{
    // Autocomplete for student page which only searches by and shows username
    $j("[name=student_username]").autocomplete({
        source: function(request, response) {
                $j.ajax({
            url: "/learn/"+base_url+"/studentlookup/",
            dataType: "json",
            data: {username: request.term},
            success: function(data) {
                var output = $j.map(data, function(item) {
                return {
                    label: item.username + " (grade " + item.grade + ")",
                    value: item.username,
                    id: item.id
                };
                });
                response(output);
            }
            });
        },
        select: function(event, ui) {
            $j(this).next("[name=student_selected]").val(ui.item.id);
        }
    });
    
    // Autocomplete for admin page which searches by and shows username and name
    $j(".student_search").autocomplete({
        source: function(request, response) {
            $j.ajax({
                url: "/admin/ajax_autocomplete/",
                dataType: "json",
                data: {
                    model_module: "esp.users.models",
                    model_name: "ESPUser",
                    ajax_func: "ajax_autocomplete_student",
                    ajax_data: request.term,
                    prog: "",
                },
                success: function(data) {
                    var output = $j.map(data.result, function(item) {
                        return {
                            label: item.ajax_str,
                            value: item.ajax_str,
                            id: item.id
                        };
                    });
                    response(output);
                }
            });
        },
        select: function(event, ui) {
            $j(this).next(".student_selected").val(ui.item.id);
        }
    });
    
    // Same as above, but filters only to students already in the lottery
    $j(".lottery_student_search").autocomplete({
        source: function(request, response) {
            $j.ajax({
                url: "/admin/ajax_autocomplete/",
                dataType: "json",
                data: {
                    model_module: "esp.users.models",
                    model_name: "ESPUser",
                    ajax_func: "ajax_autocomplete_student_lottery",
                    ajax_data: request.term,
                    prog: prog_id,
                },
                success: function(data) {
                    var output = $j.map(data.result, function(item) {
                        return {
                            label: item.ajax_str,
                            value: item.ajax_str,
                            id: item.id
                        };
                    });
                    response(output);
                }
            });
        },
        select: function(event, ui) {
            $j(this).next(".student_selected").val(ui.item.id);
        }
    });
}