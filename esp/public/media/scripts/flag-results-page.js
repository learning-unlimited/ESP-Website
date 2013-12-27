function manage (id) {
    window.open("manageclass/"+id);
}

function edit (id) {
    window.open("editclass/"+id);
}

function review (id, stat) {
    $j.post("reviewClass",
            {
                "class_id": id,
                "review_status": stat.toUpperCase(),
                "csrfmiddlewaretoken": csrf_token(),
            });
}

function approve (id) {
    review(id, "accept");
}

function unreview (id) {
    review(id, "unreview");
}

function reject (id) {
    review(id, "reject");
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
