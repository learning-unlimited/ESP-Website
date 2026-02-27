function show_hide_sidebar() {
    if (esp_user.cur_username != null) {
        $j("#main.resizable").removeClass("span12");
        $j("#main.resizable").addClass("span9");
        $j("#sidebar").removeClass("hidden");
        $j("#sidebar").addClass("span3");
    } else {
        $j("#sidebar").addClass("hidden");
        $j("#sidebar").removeClass("span3");
        $j("#main.resizable").removeClass("span9");
        $j("#main.resizable").addClass("span12");
    }
}

$j(document).ready(show_hide_sidebar);
