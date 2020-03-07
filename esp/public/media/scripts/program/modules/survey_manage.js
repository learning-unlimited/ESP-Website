$j("th.selector").click(function() {
    $details = $j("tr#details-panel");
    $rendered = $j("tr#rendered-panel");
    panel = $j(this).data("panel");
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

function updatePars(){
    var $td = $j("#id__param_values").parents("td");
    var quest_ind = $j("#id_question_type").val();
    var quest_type = $j("#id_question_type option:selected").text();
    //Delete old fields and their labels
    $j(".param_field").remove()
    if (quest_type == "Multiple Choice") {
        //Option to add/remove choices?
        console.log("hello");
    } else if (quest_type == "Labeled Numeric Rating") {
        //One field to specify number of ratings, then that many extra fields for labels
        console.log("hello2");
    } else {
        //One field for each parameter
        var params = question_types[quest_ind];
        if (params && params.length > 0) {
            $td.parents("tr").show();
            for (param of question_types[quest_ind]) {
                $td.append("<span class='param_field'>" + param + ": <input type='text' name='param_val'><br/></span>")
            }
            //Need to load parameters that have already been set
            /////////////////////////
        } else {
            //If there aren't any parameters, hide the whole row
            $td.parents("tr").hide();
        }
    }
}

function removeField(){
    
    
}

function addField(){
    
    
}

//Set up choices if question type is already chosen on page load (or hide row if not)
updatePars();

//Update choices when question type is changed
$j('#id_question_type').change(function() {
    updatePars();
});