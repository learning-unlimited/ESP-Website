var prog_url = $j('#classsearchscript').data('prog_url');

//Get choices (if there are any) for a resource via POST
function getChoices(resource_type, callback){
    var data = {furnishing: resource_type, csrfmiddlewaretoken: csrf_token()};
    $j.post('/manage/' + prog_url + '/ajaxfurnishingchoices', data, "json").success(callback);
}

//Update the option field to reflect whether there are specific choices (dropdown) or not (open response). If a value is supplied, set that value as selected afterwards.
function update_choices(resource_type_obj, choice_obj) {
    var resource_type = $j(resource_type_obj).val()
    var value = $j(choice_obj).val()
    var reactid = $j(choice_obj).data("reactid")
    getChoices(resource_type, function(response) {
        var choices = response.choices;
        if(choices[0] != "Don't care" || choices.length > 1){
            $j(choice_obj).replaceWith($j('<select data-reactid="'+reactid+'">').addClass("qb-input").attr('type', 'text'));
            var new_obj = $j('[data-reactid="'+reactid+'"]')
            $j(new_obj).data("reactid",reactid)
            $j(new_obj).append($j('<option>').text('(option)'));
            for (i in choices) {
                $j(new_obj).append($j('<option>').val(choices[i]).text(choices[i]));
            }
            if (value) {
                $j(new_obj).val(value);
            }
        } else if ($j(choice_obj).is("select")) {
            $j(choice_obj).replaceWith($j('<input data-reactid="'+reactid+'">').addClass("qb-input"));
        }
    });
}

function checkSelect(sel){
    var span = $j(sel).parent();
    if($j(span).parent().prev().children(".qb-input:not(.qb-negate)").val() == "resource"){
        var choice_obj = $j(span).next().find("input, select");
        if(choice_obj.length > 0){
            update_choices(sel, choice_obj);
        }
    }
}

function checkInput(inp){
    checkSelect($j(inp).parent().parent().prev().find("select.qb-input"));
}

//Set up choices if resource type already chosen on page load
$j.initialize("input.qb-input", function() {
    checkInput(this);
}, { target: document.getElementsByClassName('query-builder')[0] });

//Update choices when resource type is changed
$j(document).on('change', 'select.qb-input', function() {
    checkSelect(this);
});

//Update student links based on selected registrations
$j(function () {
    $j("#regtypes").change(function (){
        // Get user-selected options
        var regtypes = $j(this).val();
        var clsids = $j("#student_links").data("clsids");
        // Add reg types to all links
        $j("#student_links .dropdown-menu a").each(function (){
            var base_url = $j(this).attr('href').split('?')[0];
            $j(this).attr('href', base_url + "?clsid=" + clsids + "&regtypes=" +regtypes.join())
        });
    });
});