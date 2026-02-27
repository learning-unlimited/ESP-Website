
var test_data;

function init_jstest()
{
    var data = {};

    //  Test fetching information needed for initial display of lottery
    data_components = [
        'timeslots',
        'sections',
        'lottery_preferences'
    ];
    json_fetch(data_components, function (data) {test_data = data; console.log("Completed initial data fetch"); jstest_continue();});
}

function jstest_continue()
{
    //  Test fetching catalog information for a particular class
    update_components = [
        'class_info?section_id=5322'
    ];
    json_fetch(update_components, function (data) {test_data = data; console.log("Completed catalog data fetch: " + test_data.classes[test_data.sections[5322].parent_class].class_info);}, test_data);
}

$j(document).ready(init_jstest);


