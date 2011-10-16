function strip_tags(str)
{
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt");
}

var check_csrf_cookie = function()
{
    csrf_tokens = document.getElementsByName("csrfmiddlewaretoken");
    csrf_cookie = $j.cookie("csrftoken");
    //alert(csrf_cookie);
    if (csrf_cookie == null)
    {
        alert("Oops! It appears your session has become disconnected. Please make sure cookies are enabled and try again.");
        $j.get("/set_csrf_token");
        return false;
    }
    else
    {
        //alert("Changing csrftoken values");
        for(var i = 0; i < csrf_tokens.length; i++)
        {
            csrf_tokens[i].value = strip_tags(csrf_cookie);
            //alert("Changed to: " + strip_tags(csrf_cookie));
        }
        return true;
    }
}
