function submitAssignmentForm (event) {
    var form = $j(this);
    var data = form.serialize();
    $j.post(form.attr("action"), data, function (data) {
        form.parents("div.fqr-class").find("div.fqr-class-assignments").append(data.assignment_name);
        form.parents("div.assignment-detail").remove();
    }, 'json')
    event.preventDefault();
}

function editAssignment (url, id) {
    var input = $j("input#returned-"+id);
    var span = $j("span#fqr-assignment-header-"+id);
    $j.post(url, {'csrfmiddlewaretoken': csrf_token(), 'id' : id, 'returned': input.prop("checked") == true}, function (data) { span.replaceWith(data); });
}

function addAssignment (event) {
    var assignmentExtra = $j(event.target).parents(".fqr-class").find(".assignment-extra").last();
    var assignmentForm = assignmentExtra.clone();
    var form_select = assignmentForm.find("select");
    form_select.empty(); // remove old options
    // get and add new options
    $j.post($j(event.target).data("geturl"), {'csrfmiddlewaretoken': csrf_token(), 'secid' : $j(event.target).data("section")}, function (data) {
        if (Object.keys(data).length > 0) {
            $j.each(data, function(key,value) {
                form_select.append($j("<option></option>").attr("value", key).text(value));
            });
        } else {
            form_select.append($j("<option></option>").prop( "disabled", true ).prop( "selected", true ).text("No resources available"));
            form_select.prop( "disabled", true );
        }
    });
    assignmentForm.show().insertBefore(assignmentExtra);
}

function removeAssignment (url, id) {
    var div1 = $j("div#assignment-detail-"+id);
    var div2 = $j("span#fqr-assignment-header-"+id);
    $j.post(url, {'csrfmiddlewaretoken': csrf_token(), 'id' : id}, function () { div1.hide(); div2.hide(); });
}

$j(document).on("submit", "form.assignment-form", submitAssignmentForm)
$j(document).on("click", "button.add-assignment", addAssignment)
