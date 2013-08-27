// Initialize the json_data holder
json_data = {};

$j(document).ready(function() {
    $j(".module_group_expandable").click(function() {
	var $module_group_body = $j(this).next(".module_group_body").toggle();
	if($module_group_body.is(":visible")) {
            $j(this).children(".expand_collapse_text").text("(click to collapse)");
	}
	else {
            $j(this).children(".expand_collapse_text").text("(click to expand)");
	}
    });
});
