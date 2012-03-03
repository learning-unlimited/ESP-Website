/*
 * Javascript code for the teacher checkin module
*/

$j(function(){
    var input = $j("#shortcuts-box input");
    var selected = 0;
    
    //Replace hyphens with non-breaking hyphens, to stop Chrome from breaking up phone numbers
    function changeHyphens(n, node){
        node.innerHTML = node.innerHTML.replace(/-/g, "&#8209;");
    }
    $j(".room").map(changeHyphens);
    $j(".phone").map(changeHyphens);
    
    function updateSelected(scroll){
        var buttons = $j(".checkin");
        if(selected >= buttons.length)
            selected = buttons.length-1;
        if(selected < 0)
            selected = 0;
        buttons.removeClass("selected");
        var button = $j(buttons[selected]);
        button.addClass("selected");
        if(scroll){
            if(button.offset().top < $j(document).scrollTop() + window.innerHeight*0.25)
                $j(document).scrollTop(button.offset().top - window.innerHeight*0.25);
            if(button.offset().top > $j(document).scrollTop() + window.innerHeight*0.75)
                $j(document).scrollTop(button.offset().top - window.innerHeight*0.75);
        }
    }
    updateSelected(false);
    
    $j(".checkin").click(function(){
        var username = this.id.replace("checkin_", "");
        refresh_csrf_cookie();
        var td = this.parentNode;
        $j.post('ajaxteachercheckin', {teacher: username, csrfmiddlewaretoken: csrf_token()}, "json")
        .success(function(response) {
            td.innerHTML = response.message;
            td.previousElementSibling.className = "checked-in";
            updateSelected(false);
        }).error(function(response) {
            alert("An unknown error occured while attempting to check in " + username + ".");
        });
        this.value += "...";
    });
    
    $j(document).keypress(function(e){
        if(e.which==13){
            $j(".selected").click();
            e.preventDefault();
            input.val("");
        }
        else if(e.which==63){
            window.open($j(".selected").parent().prev().find("a")[0].href);
            e.preventDefault();
        }
    }).keydown(function(e){
        input.focus();
        if(e.which==38)
            selected--;
        else if(e.which==40)
            selected++;
        else if(e.which==33)
            selected-=5;
        else if(e.which==34)
            selected+=5;
        else
            return;
        updateSelected(true);
        e.preventDefault();
    }).keyup(function(e){
        input.change();
    });
    
    var lastLength=0;
    input.change(function(e){
        if(input.val().length > lastLength){
            var buttons = $j(".checkin");
            for(var n=0; n<buttons.length; n++)
                if(buttons[n].name.toLowerCase().indexOf(input.val().toLowerCase())==0){
                    selected=n;
                    updateSelected(true);
                    break;
                }
        }
        lastLength = input.val().length;
    });
});