var csrfmiddlewaretoken = $j.cookie("csrftoken");
if (csrfmiddlewaretoken == "")
{
    //Block on this because it's a small view and not having the cookie
    //set before the rest of the page loads would not resolve the issue
    $j.ajax("/set_csrf_token", {asyc: false});
}

function csrftoken()
{
    document.write(csrftokenstring());
}

function csrftokenstring()
{
    return "<input type='hidden' name='csrfmiddlewaretoken' value='" + csrfmiddlewaretoken + "' />";
}

function set_onsubmit()
{ 
    //Select all forms with post methods
    $j("form[method=post]")
        //Set their onsubmit functions to be check_csrf_cookie
        .submit(function() { return check_csrf_cookie(this); })
        //Filter down to ones without csrfmiddlewaretokens
        .filter(":not(:has(input[name=csrfmiddlewaretoken]))")
        //Add the csrfmiddlewaretoken hidden input
        .append(csrftokenstring())
}

$j.getScript("/media/scripts/csrf_check.js", set_onsubmit);
