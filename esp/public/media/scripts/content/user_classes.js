function update_user_classes() {
    // safety check - if esp_user does not exist
    if(!window.esp_user) return ;

    // login / logout visibility
    const isLoggedIn = !!esp_user.cur_username;
    $j(".logged_in").toggleClass("hidden", !isLoggedIn);
    $j(".not_logged_in").toggleClass("hidden", isLoggedIn);

    // update name display - the 'undefined undefined' issue
    $j("#user_first_name").text(esp_user.cur_first_name || "Guest");
    $j("#user_last_name").text(esp_user.cur_last_name || "");

    // handle admin roles
    if (esp_user.cur_admin == "1" || esp_user.cur_retTitle) {
        $j(".admin, .onsite").removeClass("hidden");
        $j(".hide-if-admin").addClass("hidden");
    }

}


$j(document).ready(update_user_classes)
