/*
 * Javascript code for the attendance module
*/

var message = '';
var lastResult = '';
Quagga.onDetected(function(result) {
    var code = result.codeResult.code;

    if (lastResult !== code) {
        beep();
        lastResult = code;
        var results = document.querySelector('textarea');
        var codes = results.value.trim().split(/\s+/).filter(Boolean);
        console.log(codes);
        if (!codes.includes(code)) {
            codes.push(code);
            results.value = codes.join("\n");
            message = code+' added to list';
        } else {
            message = code+' already in list';
        }
        $j('#scaninfo').show();
        $j('#scaninfo').html(message);
        setTimeout("$j('#scaninfo').fadeOut(); ", 4000);
    }
});

prog_url = $j('#attendancescript').data('prog_url');

function update_checkboxes(table) {
    $j(table).find("[name=attending_total]").html($j(table).find("[name=attending]:checked").length);
    $j(table).find("[name=checkedin_total]").html($j(table).find("[name=checkedin]:checked").length);
}

$j(function(){
    function markAttendance(username, secid, undo = false, callback, errorCallback){
        refresh_csrf_cookie();
        var data = {student: username, secid: secid, undo: undo, csrfmiddlewaretoken: csrf_token()};
        $j.post('/teach/' + prog_url + '/ajaxstudentattendance', data, "json").success(callback)
        .error(errorCallback);
    }

    $j("[name=attending]").change(function(){
        var checked = this.checked;
        var $me = $j(this);
        var username = $me.data("username");
        var secid = $me.data("secid");
        var $msg = $me.closest("td").find(".msg");
        var $checkedin = $me.closest("tr").find("[name=checkedin]");
        $me.prop('disabled', true);
        markAttendance(username, secid, !checked, function(response) {
            if (response.error) {
                alert(response.error);
                $me.prop("checked", !checked);
            } else {
                $me.closest("td").attr("data-st-key", (checked) ? 2 : 1);
                // If this is the webapp, we want to toggle the icons as well
                $me.siblings("i").html(checked ? "check_box" : "check_box_outline_blank");
                if (response.checkedin) {
                    $checkedin.prop("checked", true);
                    $checkedin.closest("td").attr("data-st-key", 2);
                    // If this is the webapp, we want to toggle the icons as well
                    $checkedin.siblings("i").html("check_box");
                }
                console.log(response.message);
            }
            $msg.text("");
            $me.prop('disabled', false);
            update_checkboxes($me.parents("table"));
        }, function(error) {
            alert("An error (" + error.statusText + ") occurred while attempting to update attendance for " + username + ".");
            $me.prop("checked", !checked);
            $msg.text("");
            $me.prop('disabled', false);
            // If this is the webapp, we want to toggle the icons as well
            $me.siblings("i").html(!checked ? "check_box" : "check_box_outline_blank");
        });
        $msg.text('Updating attendance...');
    });

    $j("table.sortable").each(function(i, e){
        update_checkboxes(e);
    });
});