//Formset settings
//For resource types
$j('.choice-formset').formset({
    prefix: 'resourcechoices',
    addText: 'add choice',
    deleteText: 'remove',
    addCssClass: 'choice-add',
    deleteCssClass: 'choice-delete',
    formCssClass: 'choice-dynamic-form',
});
//For classrooms
$j('.furnishing-formset').formset({
    prefix: 'furnishings',
    formTemplate: '#id_empty_form',
    addText: 'add furnishing',
    deleteText: 'remove',
    addCssClass: 'furnishing-add',
    deleteCssClass: 'furnishing-delete',
    formCssClass: 'furnishing-dynamic-form',
});

prog_url = $j('#resourcesscript').data('prog_url');

//Get choices for a furnishing via POST
function getChoices(furnishing, callback){
    var data = {furnishing: furnishing, csrfmiddlewaretoken: csrf_token()};
    $j.post('/manage/' + prog_url + '/ajaxfurnishingchoices', data, "json").success(callback);
}

//Update the option field to reflect whether there are specific choices (dropdown) or not (open response). If a value is supplied, set that value as selected afterwards.
function update_choices(furnishing_select_obj, value) {
    var furnishing = $j(furnishing_select_obj).val()
    getChoices(furnishing, function(response) {
        var choices = response.choices;
        var num = $j(furnishing_select_obj).attr('id').split("-")[1];
        $j('#id_furnishings-' + num + '-choice').remove();
        if (choices.length > 1) {
            $j(furnishing_select_obj).after($j('<select>').css('margin-left', '4px').attr('id','id_furnishings-' + num + '-choice').attr('name','furnishings-' + num + '-choice').attr('type', 'text'));
            $j('#id_furnishings-' + num + '-choice').append($j('<option>').text('(option)'));
            for (i in choices) {
                $j('#id_furnishings-' + num + '-choice').append($j('<option>').val(choices[i]).text(choices[i]));
            }
        } else {
            $j(furnishing_select_obj).after($j('<input>').css('margin-left', '4px').attr('id','id_furnishings-' + num + '-choice').attr('name','furnishings-' + num + '-choice').attr('maxlength', '50').attr('placeholder', '(option)').attr('type', 'text'));
        }
        if (value) {
            $j('#id_furnishings-' + num + '-choice').val(value);
        }
    });
}

//Upon page load and dynamic creation of new selects
$j.initialize("select", function() {
    //Selects start with (option) or (furnishing) by default, but we want to hide these as options in the dropdown.
    var opt = $j(this).find("option")[0];
    $j(opt).hide();
    $j(opt).css("display", "none");
    opt.disabled = true;
    //Convert option field to dropdown if necessary
    if ($j(this).attr('id').split("-")[2] == "furnishing") {
        var num = $j(this).attr('id').split("-")[1];
        //Make sure to preserve selected value
        var value = $j('#id_furnishings-' + num + '-choice').val();
        if (value) {
            update_choices($j(this), value);
        }
    }
}, { target: document.getElementById('furnishing_formset') });

//Whenever a new furnishing is selected, update the respective option field
$j('.furnishing-dynamic-form select').change(function() {
    update_choices($j(this));
});