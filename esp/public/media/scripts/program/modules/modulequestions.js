
$(document).ready(function(){
    // when the page loads, check/select the questions induced by the modules
    // that are already selected (if any, from a template program e.g.)
    modulesToQuestions();

    // questionsToModules should be called when the form gets submitted
});


function questionsToModules() {
    var nQuestions = $j("#id_program_module_questions").children().length;
    var modules = [];
    for (i=0; i < nQuestions; i++) {
        modules += $j("#id_program_module_questions_"+i).val().split(",")
    }
    // Now just check those in the list.
    $j.uniqueSort(modules);
    $j("#id_program_modules").val(modules);
    return
};


// Given the list of selected modules in the program_modules MultipleChoiceField,
// check the checkboxes in the program modules questions list that they induce
// This is hard-coded based on our knowledge of modules and needs to be
// updated as new modules are introduced.
function modulesToQuestions() {
    // the IDs of the modules currently selected
    var currentlySelectedIds = $j("select#id_program_modules").val();
    // if there are none, skip the rest of this
    if (currentlySelectedIds.length == 0)
        return
    // otherwise, get the questions and see whether we should check them
    var questions = $j("#id_program_module_questions").children()
    // start by clearing all selections
    for (i=0; i < nQuestions; i++)
    // get the
    for (i=0; i < questions.length; i++) {
        var q = questions[i];
        var qvalslist = q.firstChild.firstChild.value.split(",");
        var include = true;
        if (qvalslist.length == 0) {
            alert("The following question is associated with zero modules! "
                  + "Please contact web support.\n"
                  + q.textContent);
        }
        else {
            for (j=0; j < qvalslist.length; j++) {
                if (!currentlySelectedIds.includes(qvalslist[j])) {
                    include = false;
                }
            }
            $j("#id_program_module_questions_" + i).prop("checked", include);
        }
    return
};
