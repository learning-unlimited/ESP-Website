// Non-admins may still be able to edit specific QSDs (e.g., teachers on their
// class pages), so ask the server which of this page's QSDs they can edit.
function reveal_editable_qsd_bits() {
    var $bits = $j(".qsd_bits[data-qsd-url]");
    var urls = [];
    $bits.each(function () {
        var url = $j(this).attr("data-qsd-url");
        if (urls.indexOf(url) == -1) {
            urls.push(url);
        }
    });
    if (urls.length == 0) {
        return;
    }

    $j.getJSON("/admin/ajax_qsd_can_edit", $j.param({url: urls}, true), function (data) {
        $bits.each(function () {
            if (data.editable.indexOf($j(this).attr("data-qsd-url")) != -1) {
                $j(this).removeClass("hidden");
            }
        });
    });
}

function update_user_classes() {
    if (esp_user.cur_retTitle) {
        $j("#unmorph_text").html(
            "Click above to return to your administrator account - " +
            esp_user.cur_retTitle
        );
    }

    if (esp_user.cur_qsd_bits == "1") {
        $j(".qsd_bits").removeClass("hidden");
    } else if (esp_user.cur_username) {
        reveal_editable_qsd_bits();
    }

    var type_name = "";
    for (var i = 0; i < esp_user.cur_roles.length; i++) {
        type_name = "." + esp_user.cur_roles[i];
    // This is wrapped in a try/catch block because custom user role names
    // might not be in a format that jQuery accepts as a selector.
        try {
            $j(type_name).removeClass("hidden");
        } catch (e) {}
    }
}

$j(document).ready(update_user_classes);