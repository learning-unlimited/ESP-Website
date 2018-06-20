function manage (id) {
    window.open("manageclass/"+id);
}

function edit (id) {
    window.open("editclass/"+id);
}

function review (id, stat, text, color) {
    $j.post("reviewClass",
            {
                "class_id": id,
                "review_status": stat.toUpperCase(),
                "csrfmiddlewaretoken": csrf_token(),
            }, function () {
                $j("#fqr-class-"+id+" .class-status").html(text).css("color",color);
                $j("#fqr-class-"+id+" .fqr-class-header").removeClass("accepted rejected unreviewed").addClass(text.toLowerCase())
            });
}

function approve (id) {
    review(id, "accept", "Accepted", "#0C0");
}

function unreview (id) {
    review(id, "unreview", "Unreviewed", "#00C");
}

function reject (id) {
    review(id, "reject", "Rejected", "#C00");
}

function deleteClass (id, name) {
    if (confirm("Are you sure you want to delete the class "+name+"?  This action cannot be undone.")) {
        $j.post("deleteclass/"+id,
                { "csrfmiddlewaretoken": csrf_token() },
                success=function () {
                    $j("#fqr-class-"+id).remove();
        });
    }
}

function emailTeachers (emailAddress, subject) {
    window.open("mailto:" + emailAddress + '?subject=' + encodeURIComponent(subject));
}

function showAll () {
    $j(".fqr-class-detail").show();
    $j(".flag-detail:not(.flag-extra)").show();
}

function showWithComments () {
    $j(".fqr-class-detail").show();
    $j(".flag-detail.flag-has-comment").show();
}

function hideAll () {
    $j(".fqr-class-detail").hide();
    $j(".flag-detail").hide();
}

function approveAll () {
    $j("#program_form .btn-approve").click();
}

function unreviewAll () {
    $j("#program_form .btn-unreview").click();
}

function rejectAll () {
    $j("#program_form .btn-reject").click();
}

$j(document).ready(function () {
    $j(".flag-detail").hide();
    $j(".manage-approve-link").hide();
});
