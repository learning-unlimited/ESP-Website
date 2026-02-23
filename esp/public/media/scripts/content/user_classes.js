function normalize_user_value(value) {
    if (value === undefined || value === null) {
        return '';
    }
    var normalized = String(value);
    if (normalized === 'undefined' || normalized === 'null') {
        return '';
    }
    return normalized;
}

function get_user_greeting_name(first_name, username) {
    var cleaned_first_name = normalize_user_value(first_name).trim();
    var cleaned_username = normalize_user_value(username).trim();

    if (cleaned_first_name) {
        return cleaned_first_name;
    }
    if (cleaned_username) {
        return cleaned_username;
    }
    return "Guest";
}

function update_user_classes() {
    if (esp_user.cur_admin == "1" || esp_user.cur_retTitle) {
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
    var first_name = normalize_user_value(esp_user.cur_first_name);
    var last_name = normalize_user_value(esp_user.cur_last_name);
    var username = normalize_user_value(esp_user.cur_username);
    var user_id = esp_user.cur_userid;
    if (user_id === undefined || user_id === null || user_id !== user_id) {
        user_id = '';
    }

    $j("#user_greeting_name").text(get_user_greeting_name(first_name, username));
    $j("#user_first_name").text(first_name);
    $j("#user_last_name").text(last_name);
    $j("#user_username").text(username);
    $j("#user_userid").text(user_id);
}

$j(document).ready(update_user_classes)
