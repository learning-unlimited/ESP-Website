/*
 * Javascript code for the teacher checkin module
*/

$j(function(){
    var input = $j("#shortcuts-box input");
    var selected = 0;
    var checkins = [];

    $j(".flag-detail").hide();
    $j(".flag-header").removeClass("active");
    $j(".assignment-detail").hide();

    //Replace hyphens with non-breaking hyphens, to stop Chrome from breaking up phone numbers
    function changeHyphens(n, node){
        node.innerHTML = node.innerHTML.replace(/-/g, "&#8209;");
    }
    $j(".room").map(changeHyphens);
    $j(".phone").map(changeHyphens);

    $j('.section-detail-header').click(function () {
        $j(this).toggleClass('active');
        var info = $j(this).closest("tr").nextAll(".section-detail-tr").first().find('.section-detail-info');
        var class_id = info.attr('data-class-id');

        // Let data-class-id indicate which class id we want to load details
        // for, as well as whether we still want to load them.
        if (class_id !== '') {

          // Clear the attribute while we're attempting to load details so that
          // we don't try multiple requests for the same class concurrently.
          info.attr('data-class-id', '');

          $j.ajax({
            method: 'GET',
            url: 'ajaxclassdetail',
            data: {
              'class': class_id,
              show_flags: info.attr('data-show-flags'),
            },
            success: function (result) {
              info.html(result);
            },
            error: function (xhr, status, errorThrown) {
              // If an attempt at loading details fails, restore data-class-id
              // so we can try again if the user so requests.
              info.text(errorThrown);
              info.attr('data-class-id', class_id);
            },
          });
        }
        info.toggle('blink');
    });

    function updateSelected(scroll){
        var buttons = $j('.checkin:enabled');
        if(selected >= buttons.length)
            selected = buttons.length-1;
        if(selected < 0)
            selected = 0;
        $j(".selected").removeClass("selected");
        var button = $j(buttons[selected]);
        button.parent().parent().addClass("selected");
        if(scroll){
            if(button.offset().top < $j(document).scrollTop() + window.innerHeight*0.25)
                $j(document).scrollTop(button.offset().top - window.innerHeight*0.25);
            if(button.offset().top > $j(document).scrollTop() + window.innerHeight*0.75)
                $j(document).scrollTop(button.offset().top - window.innerHeight*0.75);
        }
        if(checkins.length>0)
            $j("#last_checkin").html(checkins[checkins.length-1].name).parent().show();
        else
            $j("#last_checkin").parent().hide();
    }
    updateSelected(false);

    function checkIn(username, callback, undo, errorCallback){
        refresh_csrf_cookie();
        var data = {teacher: username, csrfmiddlewaretoken: csrf_token()};
        if(undo)
            data.undo = true;
        $j.post('ajaxteachercheckin', data, "json").success(callback)
        .error(function(){
            alert("An error occurred while atempting to " + (undo?"un-check-in ":"check-in ") + username + ".");
            if (errorCallback) {
                errorCallback();
            }
        });
    }

    function checkInById(id, callback, undo, errorCallback){
        refresh_csrf_cookie();
        var data = {teacherid: id, csrfmiddlewaretoken: csrf_token()};
        if(undo)
            data.undo = true;
        $j.post('ajaxteachercheckin', data, "json").success(callback)
        .error(function(){
            alert("An error occurred while atempting to " + (undo?"un-check-in ":"check-in ") + username + ".");
            if (errorCallback) {
                errorCallback();
            }
        });
    }

    function undoCheckIn(username, callback, errorCallback){
        checkIn(username, callback, true, errorCallback);
    }

    $j(".checkin:enabled").click(function(){
        var username = $j(this).data("username").replace("checkin_", "");
        var $td = $j(this.parentNode);
        var $msg = $td.children('.message');
        var tds = [$td]
        checkIn(username, function(response) {
            $j("[data-username='checkin_" + username +"']:not([disabled])").each(function() {
                var $me = $j(this);
                var $td = $j(this.parentNode);
                var $msg = $td.children('.message');
                var $txtbtn = $j(this).closest('tr').find('.text');
                
                $msg.text(response.message);
                $td.prev().prop('class', 'checked-in');
                $me.hide().prop('disabled', true);
                $txtbtn.prop('disabled', true);
                $txtbtn.attr("title","Teacher already checked-in");
                updateSelected(false);

                var $undoButton = $j(document.createElement('button'));
                $undoButton.prop('class', 'btn btn-default btn-mini undo-button');
                $undoButton.text('Undo');
                $undoButton.click(function () {
                    undoLiveCheckIn(username);
                });
                $msg.append(' ', $undoButton);
                tds.push($td);
            });
            checkins.push({username: username, name: response.name, $tds: tds});
        });
        $msg.text('Checking in...');
    });

    function sendText(user, sec, callback, errorCallback){
        var data = {username: user, section: sec, csrfmiddlewaretoken: csrf_token()};
        $j.post('ajaxteachertext', data, "json").success(callback)
        .error(function(){
            alert("An error occurred while atempting to text " + user + ".");
            if (errorCallback) {
                errorCallback();
            }
        });
    }

    function textTeacher(btn) {
        var username = $j(btn).data("username");
        var section = $j(btn).data("section");
        var msg = $j(btn).closest('td').find('.message');
        sendText(username, section, function(response) {
            $j(msg).text(response.message);
        });
        $j(btn).attr("disabled",true);
        $j(btn).attr("title","Teacher already texted");
        $j(msg).text('Texting teacher...');
    }

    $j(".text").click(function(){
        textTeacher($j(this))
    });

    var skip_semi_checked_in_teachers = false
    $j("#skip-semi-checked-in-teachers").click(function() {
        skip_semi_checked_in_teachers = this.checked;
    });

    $j(".text-all-teachers").click(function(){
        var $buttons = $j(".checkin:visible").closest('tr[data-role="teacher"]').find('.text:enabled');
        if (skip_semi_checked_in_teachers) {
            var keep = [];
            for (var i = 0; i < $buttons.length; i++) {
                var teacher = $j($buttons[i]).closest('tr[data-role="teacher"]');
                var sec_id = $j(teacher).data("sec-id");
                if ($j(teacher).siblings("[data-sec-id='" + sec_id + "']").find("td.checked-in").length == 0) {
                    keep.push($buttons[i]);
                }
            }
            $buttons = $j($buttons).filter(keep);
        }
        var num_teachers = $buttons.length;
        var r = confirm("Are you sure you'd like to text " + num_teachers + " unchecked-in teachers?");
        if (r) {
            $buttons.each(function() {
                textTeacher($j(this));
            });
        }
    });

    var skip_semi_checked_in_moderators = false
    $j("#skip-semi-checked-in-moderators").click(function() {
        skip_semi_checked_in_moderators = this.checked;
    });

    $j(".text-all-moderators").click(function(){
        var $buttons = $j(".checkin:visible").closest('tr[data-role="moderator"]').find('.text:enabled');
        if (skip_semi_checked_in_moderators) {
            var keep = [];
            for (var i = 0; i < $buttons.length; i++) {
                var teacher = $j($buttons[i]).closest('tr[data-role="moderator"]');
                var sec_id = $j(teacher).data("sec-id");
                if ($j(teacher).siblings("[data-sec-id='" + sec_id + "']").find("td.checked-in").length == 0) {
                    keep.push($buttons[i]);
                }
            }
            $buttons = $j($buttons).filter(keep);
        }
        var num_teachers = $buttons.length;
        var r = confirm("Are you sure you'd like to text " + num_teachers + " unchecked-in " + moderator_title + "s?");
        if (r) {
            $buttons.each(function() {
                textTeacher($j(this));
            });
        }
    });

    $j(".uncheckin:enabled").click(function(){
        var username = $j(this).data("username").replace("uncheckin_", "");
        undoCheckIn(username, function(response) {
            alert(response.message);
            location.reload();
        });
        this.value += "...";
    });

    // Undo the check in of the user with the specified username, assuming
    // that that user was not checked in when this page was loaded (because
    // the DOM would look different depending on whether that were true). If
    // no username specified, undo the last check in.
    function undoLiveCheckIn(username) {
        var targetCheckin;
        if (username === undefined) {
            if (checkins.length === 0) {
                return false;
            }
            targetCheckin = checkins[checkins.length - 1];
        } else {
            // search from the back because we assume more recent checkins
            // are more likely to be undone
            // (TODO if undoing changes from long ago is actually used a lot:
            // make this a hash)
            for (var i = checkins.length - 1; i >= 0; i--) {
                if (checkins[i].username === username) {
                    targetCheckin = checkins[i];
                    break;
                }
            }
        }
        if (targetCheckin === undefined) {
            alert("No check-in for " + username + " found to undo");
            return;
        }
        username = targetCheckin.username;
        var $tds = targetCheckin.$tds;
        var $msg = $tds[0].children('.message');
        var $undoButton = $msg.children('.undo-button');
        $undoButton.text('Undoing...').prop('disabled', true);
        undoCheckIn(username, function(response) {
            // find targetCheckin in checkins and splice it out
            for (var i = checkins.length - 1; i >= 0; i--) {
                if (checkins[i] === targetCheckin) {
                    checkins.splice(i, 1);
                    break;
                }
            }
            for (var $td of $tds) {
                $td.children('.checkin').show().prop('disabled', false);
                $td.closest('tr').find('.text').prop('disabled', false).removeAttr("title");
                $td.prev().prop('class', 'not-checked-in');
                $td.children('.message').html("");
            }
            $msg.html(response.message+"<br/>");
            selected = $j('.checkin:enabled').index($tds[0].find('.checkin'));
            updateSelected(true);
        }, function() {
            // on error, re-enable undo so you can try again
            $undoButton.text('Undo').prop('disabled', false);
        });
    }

    $j(document).keydown(function(e){
        if(e.target.nodeName !== "TEXTAREA" && e.target.id !== "user_search_field" && e.target.id !== "class_search_field") { // Prevent capturing textarea typing
            if(/^[a-z0-9]$/i.test(e.key) && !e.ctrlKey) { // Normal text
                if(e.target !== input[0]) // Reset input if not target
                    input.val("");
                input.focus(); // Focus input for rest of text input
            }
            else if([38, 40, 33, 34].includes(e.which)) { // Change selected teacher by one or five
                if(e.which==38) // Up arrow
                    selected--;
                else if(e.which==40) // Down arrow
                    selected++;
                else if(e.which==33) // Page up
                    selected-=5;
                else if(e.which==34) // Page down
                    selected+=5;
                e.preventDefault();
                updateSelected(true);
            }
            else if(e.which==90 && e.ctrlKey){ // Ctrl + z
                undoLiveCheckIn();
                e.preventDefault();
            }
            else if(e.which==13 && e.shiftKey){ // Shift + Enter
                $j(".selected .checkin").click(); // Check in teacher
                e.preventDefault();
                input.val("");
            }
            else if(e.which==13){
                checkInById(input.val(), function(response) {
                    if (response.username) {
                        var username = response.username;
                        var tds = []
                        $j("[data-username='checkin_" + username +"']:not([disabled])").each(function() {
                            var $me = $j(this);
                            var $td = $j(this.parentNode);
                            var $msg = $td.children('.message');
                            var $txtbtn = $j(this).closest('tr').find('.text');
                            
                            $msg.text(response.message);
                            $td.prev().prop('class', 'checked-in');
                            $me.hide().prop('disabled', true);
                            $txtbtn.prop('disabled', true);
                            $txtbtn.attr("title","Teacher already checked-in");

                            var $undoButton = $j(document.createElement('button'));
                            $undoButton.prop('class', 'btn btn-default btn-mini undo-button');
                            $undoButton.text('Undo');
                            $undoButton.click(function () {
                                undoLiveCheckIn(username);
                            });
                            $msg.append(' ', $undoButton);
                            tds.push($td);
                        });
                        checkins.push({username: username, name: response.name, $tds: tds});
                        updateSelected(false);
                    }
                    input.next(".message").html(response.message);
                    input.next(".message").show();
                    setTimeout("$j('#shortcuts-box input').next('.message').fadeOut(); ", 4000);
                });
                input.val("");
            }
            else if(e.which==191 && e.shiftKey){ // Shift + ?
                window.open($j(".selected a")[0].href); // Open userview page
                e.preventDefault();
            }
        }
    }).keyup(function(e){
        if(e.target.nodeName !== "TEXTAREA" && e.target.id !== "user_search_field" && e.target.id !== "class_search_field")
            input.change();
    });

    var lastLength=0;
    input.change(function(e){
        if(input.val().length == 0)
            input.removeClass();
        else if(input.val().length > lastLength || input.hasClass("not-found")){
            var found=false;
            var buttons = $j(".checkin:not([disabled])");
            try { // Find first matching teacher or section
                var patt = new RegExp(input.val().toLowerCase());
                for(var n=0; !found && n<buttons.length; n++) // Loop through section codes/titles
                    if(patt.test(buttons[n].name.toLowerCase())){
                        selected=n;
                        found=true;
                    }
                for(var n=0; !found && n<buttons.length; n++) // Loop through teacher names
                    if(patt.test($j(buttons[n]).parent().prev().children("a").html().toLowerCase())){
                        selected=n;
                        found=true;
                    }
                if(found)
                    updateSelected(true);
                input.removeClass().addClass(found?"found":"not-found");
            } catch(e) {
                // Unselect teacher and make input white until we get a valid expression
                input.removeClass();
                $j(".selected").removeClass("selected");
            }
        }
        lastLength = input.val().length;
    });

    var lastResult = '';
    Quagga.onDetected(function(result) {
        var code = result.codeResult.code;

        if (lastResult !== code) {
            lastResult = code;
            beep();
            checkInById(code, function(response) {
                if (response.username) {
                    var username = response.username;
                    var tds = []
                    $j("[data-username='checkin_" + username +"']:not([disabled])").each(function() {
                        var $me = $j(this);
                        var $td = $j(this.parentNode);
                        var $msg = $td.children('.message');
                        var $txtbtn = $j(this).closest('tr').find('.text');
                        
                        $msg.text(response.message);
                        $td.prev().prop('class', 'checked-in');
                        $me.hide().prop('disabled', true);
                        $txtbtn.prop('disabled', true);
                        $txtbtn.attr("title","Teacher already checked-in");

                        var $undoButton = $j(document.createElement('button'));
                        $undoButton.prop('class', 'btn btn-default btn-mini undo-button');
                        $undoButton.text('Undo');
                        $undoButton.click(function () {
                            undoLiveCheckIn(username);
                        });
                        $msg.append(' ', $undoButton);
                        tds.push($td);
                    });
                    checkins.push({username: username, name: response.name, $tds: tds});
                    updateSelected(false);
                }
                $j('#scaninfo').show();
                $j('#scaninfo').html(response.message);
                setTimeout("$j('#scaninfo').fadeOut(); ", 4000);
            });
        }
    });
});
