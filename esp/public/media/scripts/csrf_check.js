dojo.require('dijit.form.Button');
dojo.require('dijit.Dialog');

if($j("#csrfAlert").length == 0)
{
    newDiv = document.createElement('div');
    newDiv.setAttribute('id', 'csrfAlert');
    newDiv.setAttribute('dojoType', 'dijit.Dialog');
    newDiv.setAttribute('style', 'display:none');
    newDiv.setAttribute('title', 'Oops!');
    newText = document.createTextNode('It appears your session has become disconnected. Please make sure cookies are enabled and try again.');
    newDiv.appendChild(newText);
    document.body.appendChild(newDiv);
}

function strip_tags(str)
{
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt");
}

var check_csrf_cookie = function(form)
{
    //If the form is null, return false
    if (!form) return false;

    //Check if the form is external
    var hostname = new RegExp(location.host);
    var prefix = new RegExp("[A-Za-z-].*://");
    if (prefix.test(form.action) && !hostname.test(form.action))
    {
        //Delete the csrfmiddlewaretoken if it has it
        $j(form).find("input[name=csrfmiddlewaretoken]").remove();
        return true;
    }

    //Set the csrf token
    $j.ajax("/set_csrf_token", { async: false });

    //If this form is missing the csrfmiddlewaretoken, add it
    if (!form.csrfmiddlewaretoken)
    {
        console.log('Missing csrfmiddlewaretoken, adding');
        $j(form).append(csrftokenstring());
    }

    //Check it
    csrf_token = $j(form.csrfmiddlewaretoken).val();
    console.log(csrf_token);
    csrf_cookie = $j.cookie("csrftoken");
    if (csrf_cookie == null)
    {
        dijit.byId('csrfAlert').show();
        return false;
    }

    if (csrf_cookie != form.csrfmiddlewaretoken)
    {
        console.log('Not matching. csrf_cookie: ' + csrf_cookie + ', csrfmiddlewaretoken: ' + csrf_token);
    }
    return true;
    /*



    //alert(csrf_cookie);

    else
    {
        //alert("Changing csrftoken values");
        csrf_token.value = strip_tags(csrf_cookie);
        //alert("Changed to: " + strip_tags(csrf_cookie));
        //alert("csrf_token = " + csrf_token.value + ", csrf_cookie = " + csrf_cookie);
        return true;
    }



    */
}
