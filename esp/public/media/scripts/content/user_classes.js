function update_user_classes() {
    if (esp_user.cur_admin == "1" || esp_user.cur_retTitle) {
        $j(".admin").removeClass("hidden");
        $j(".onsite").removeClass("hidden");
        $j(".hide-if-admin").addClass("hidden");
    }

    if (esp_user.cur_retTitle) {
        $j(".unmorph").removeClass("hidden");
        $j("#unmorph_text").html(
            "Click above to return to your administrator account - " +
            esp_user.cur_retTitle
        );
    }

    if (esp_user.cur_qsd_bits == "1") {
        $j(".qsd_bits").removeClass("hidden");
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