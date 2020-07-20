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

$j(function(){
    function markAttendance(username, secid, undo = false, callback, errorCallback){
        refresh_csrf_cookie();
        var data = {student: username, secid: secid, undo: undo, csrfmiddlewaretoken: csrf_token()};
        $j.post('/teach/' + prog_url + '/ajaxstudentattendance', data, "json").success(callback)
        .error(function(){
            alert("An error occurred while atempting to update attendance for" + username + ".");
            if (errorCallback) {
                errorCallback();
            }
        });
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
            $me.closest("td").attr("sorttable_customkey", (checked) ? 2 : 1);
            if (response.checkedin) {
                $checkedin.prop("checked", true);
                $checkedin.closest("td").attr("sorttable_customkey", 2);
            }
            $msg.text(response.message);
            $me.prop('disabled', false);
        });
        $msg.text('Updating attendance...');
    });
});