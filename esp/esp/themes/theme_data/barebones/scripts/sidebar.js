function show_hide_sidebar() {
    if (esp_user.cur_username != null) {
        $j("#main.resizable").removeClass("col-md-12");
        $j("#main.resizable").addClass("col-md-9");
        $j("#sidebar").removeClass("hidden");
        $j("#sidebar").addClass("col-md-3");
    } else {
        $j("#sidebar").addClass("hidden");
        $j("#sidebar").removeClass("col-md-3");
        $j("#main.resizable").removeClass("col-md-9");
        $j("#main.resizable").addClass("col-md-12");
    }
}

$j(document).ready(show_hide_sidebar);
