$j("th.selector").click(function() {
    var $details = $j("tr#details-panel");
    var $rendered = $j("tr#rendered-panel");
    var panel = $j(this).data("panel");
    $j(this).addClass("active");
    if (panel == "details"){
        $details.show();
        $rendered.hide();
        $j("th.selector[data-panel='rendered']").removeClass("active");
    } else if (panel == "rendered") {
        $details.hide();
        $rendered.show();
        $j("th.selector[data-panel='details']").removeClass("active");
    }
});

if (typeof question_types != 'undefined') {
    var par_values = $j("#id__param_values").text().split("|");

    function updatePars(){
        var $td = $j("#id__param_values").parents("td");
        var quest_ind = $j("#id_question_type").val();
        var quest_type = $j("#id_question_type option:selected").text().split(":")[0];
        //Delete old fields and their labels
        $j(".param_field, .param_extra_field").remove();
        if (["Multiple Choice", "Checkboxes"].includes(quest_type)) {
            var num_choices = (par_values.length > 1)? par_values.length : 5;
            //Add field for user to specify number of choices
            $td.append("<span class='param_extra_field'>Number of choices: <input type='text' id='num_choices' value='" + num_choices + "'><br/></span>");
            //We want to prevent people from submitting the form by pressing enter
            $td.append("<button class='param_extra_field' type='submit' disabled hidden></button>");
            //Add fields for choices
            for (let i = 0; i < num_choices; i++) {
                var par_value = (i in par_values)? par_values[i] : "";
                $td.append("<span class='param_field'>Choice " + (i + 1) + ": <input type='text' name='param_val' value='" + par_value + "'><br/></span>");
            }
            updateVals();
            $j("#num_choices").change(function() {
                num_choices = $j(this).val();
                var $fields = $j(".param_field");
                //Add extra fields if necessary
                for (let i = 0; i < num_choices; i++) {
                    if ($fields[i] === undefined){
                        $td.append("<span class='param_field'>Choice " + (i + 1) + ": <input type='text' name='param_val'><br/></span>");
                    }
                }
                //Remove extra fields if necessary
                $fields.slice(num_choices).remove();
                updateVals();
            });
            $td.parents("tr").show();
        } else if (quest_type == "Labeled Numeric Rating") {
            var num_ratings = (par_values.length > 1)? par_values.length - 1 : 5;
            //Add field for user to specify number of ratings
            $td.append("<span class='param_extra_field'>Number of ratings: <input type='text' id='num_ratings' name='param_val' value='" + num_ratings + "'><br/></span>");
            //We want to prevent people from submitting the form by pressing enter
            $td.append("<button class='param_extra_field' type='submit' disabled hidden></button>");
            //Add fields for rating labels
            for (let i = 1; i < (num_ratings + 1); i++) {
                var par_value = (i in par_values)? par_values[i] : "";
                $td.append("<span class='param_field'>Rating " + i + ": <input type='text' name='param_val' value='" + par_value + "'><br/></span>");
            }
            updateVals();
            //Update number of fields if requested
            $j("#num_ratings").change(function() {
                num_ratings = $j(this).val();
                var $fields = $j(".param_field");
                //Add extra fields if necessary
                for (let i = 0; i < num_ratings; i++) {
                    if ($fields[i] === undefined){
                        $td.append("<span class='param_field'>Rating " + (i + 1) + ": <input type='text' name='param_val'><br/></span>");
                    }
                }
                //Remove extra fields if necessary
                $fields.slice(num_ratings).remove();
                updateVals();
            });
            $td.parents("tr").show();
        } else {
            //One field for each parameter
            var params = question_types[quest_ind];
            if (params && params.length > 0) {
                for (let i = 0; i < params.length; i++) {
                    var par_value = (i in par_values)? par_values[i] : "";
                    $td.append("<span class='param_field'>" + params[i] + ": <input type='text' name='param_val' value='" + par_value + "'><br/></span>");
                }
                $td.parents("tr").show();
            } else {
                //If there aren't any parameters, hide the whole row
                $td.parents("tr").hide();
            }
            updateVals();
        }
    }

    function updateTextArea() {
        par_values = [];
        $j("[name=param_val]").each(function() {
            par_values.push($j(this).val());
        });
        $j("#id__param_values").text(par_values.join("|"));
    }

    function updateVals() {
        updateTextArea();
        $j("[name=param_val]").on('input', function() {
            updateTextArea();
        });
    }

    //Set up choices if question type is already chosen on page load (or hide row if not)
    updatePars();

    //Update choices when question type is changed
    $j('#id_question_type').change(function() {
        updatePars();
    });
}

//Stuff specific to the import page
function toggleAll(source) {
    $j('[type=checkbox]').prop('checked', source.checked);
}

function toggle(source) {
    $j('[value=' + $j(source).val() + ']').prop('checked', source.checked);
    if ($j('[name=to_import]:checked').length == 0) {
        $j('.toggleall').prop('checked', false);
    } else if ($j('[name=to_import]:checked').length == $j('[name=to_import]').length) {
        $j('.toggleall').prop('checked', true);
    }
}


