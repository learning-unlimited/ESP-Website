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
        // $j("#main.resizable").removeClass("span12");
        // $j("#main.resizable").addClass("span9");
        // $j("#sidebar").removeClass("hidden");
        // $j("#sidebar").addClass("span3");
    } else {
        $j(".not_logged_in").removeClass("hidden");
        $j(".logged_in").addClass("hidden");
        // $j("#sidebar").addClass("hidden");
        // $j("#sidebar").removeClass("span3");
        // $j("#main.resizable").removeClass("span9");
        // $j("#main.resizable").addClass("span12");
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
    // $j("#loginbox_user_name").html("Hello, " + esp_user.cur_first_name + " " + esp_user.cur_last_name + "<br /><span style='color: #444; font-style: italic;'>" + esp_user.cur_username + " / " + esp_user.cur_userid + "</span>");
    var name = (esp_user.cur_first_name && esp_user.cur_last_name) ? esp_user.cur_first_name + " " + esp_user.cur_last_name : esp_user.cur_userid;
    $j("#loginbox_user_name").text(name);
}
