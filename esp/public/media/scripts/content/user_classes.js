function update_user_classes() {
    if (esp_user.cur_admin == "1") {
        $j(".admin").removeClass("hidden");
        $j(".onsite").removeClass("hidden");
        $j(".hide-if-admin").addClass("hidden");
    }
    if (esp_user.cur_retTitle) {
        $j(".unmorph").removeClass("hidden");
        $j("#unmorph_text").html("Click above to return to your administrator account - " + esp_user.cur_retTitle);
    }
    if (esp_user.cur_qsd_bits == "1") {
        $j(".qsd_bits").removeClass("hidden");
    }
    if (esp_user.cur_username != null) {
        $j(".not_logged_in").addClass("hidden");
        $j(".logged_in").removeClass("hidden");
    } else {
        $j(".not_logged_in").removeClass("hidden");
        $j(".logged_in").addClass("hidden");
    }

    var type_name = '';
    var hidden_name = '';
    for (var i = 0; i < esp_user.cur_roles.length; i++) {
        type_name = "." + esp_user.cur_roles[i];
        try {
            // This is wrapped in a try/catch block, because custom user
            // role names might not be in a format that jQuery accepts.
            $j(type_name).removeClass("hidden");
        } catch (e) {}
    }
    
    //    Write user's name in the appropriate spot in the login box
    $j("#user_first_name").text(esp_user.cur_first_name);
    $j("#user_last_name").text(esp_user.cur_last_name);
    $j("#user_username").text(esp_user.cur_username);
    $j("#user_userid").text(esp_user.cur_userid);
}

$j(document).ready(update_user_classes)
