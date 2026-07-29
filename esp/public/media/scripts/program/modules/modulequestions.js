$j(document).ready(function(){
    // when the page loads, check/select the questions induced by the modules
    // that are already selected (if any, from a template program e.g.)
    $j(".hidden-field").parents("tr").hide()
    modulesToQuestions();
    
    // when any question is checked/unchecked, add/remove only those modules
    $j("#id_program_module_questions").find("input").change(function(){
        var modules = $j("#id_program_modules").val();
        var checkbox_modules = $j(this).val().split(",");
        if ($j(this).prop("checked")) {
            modules = $j.merge(modules, checkbox_modules);
        } else {
            modules = _.without(modules, ...checkbox_modules);
        }
        $j("#id_program_modules").val(_.uniq(modules));
    });
});


// called when the form gets submitted
function questionsToModules() {
    var modules = $j("#id_program_modules").val();
    // Check if there is a nonzero admissions fee entered; if so, add the associated modules
    if ($j("#id_base_cost").val() != "" && parseInt($j("#id_base_cost").val()) > 0) {
        var modules_to_check = $j("#id_program_modules").children().filter(function(index){
                                                                           return ["Accounting", "Financial Aid Application",
                                                                                   "Easily Approve Financial Aid Requests"].includes($j(this).text());});
        $j.merge(modules, modules_to_check.map(function(index){return this.value;}));
    }
    // Now just check those modules in the list.
    $j("#id_program_modules").val(_.uniq(modules));
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
    if (currentlySelectedIds == null || currentlySelectedIds.length == 0)
        return
    // otherwise, get the questions and see whether we should check them
    var questions = $j("#id_program_module_questions").children();
    // check if ALL the modules associated with a given question are selected
    // if so, check that box
    for (var i=0; i < questions.length; i++) {
        var q = questions[i];
        var qvalslist = q.firstChild.firstChild.value.split(",");
        var include = true;
        if (qvalslist.length == 0) {
            alert("The following question is associated with zero modules! "
                  + "Please contact web support.\n"
                  + q.textContent);
        }
        else {
            for (var j=0; j < qvalslist.length; j++) {
                if (!currentlySelectedIds.includes(qvalslist[j])) {
                    include = false;
                    break
                }
            }
            $j("#id_program_module_questions_" + i).prop("checked", include);
        }
    }
    return
};
