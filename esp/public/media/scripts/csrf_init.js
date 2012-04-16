function csrf_token()
{
    return $j.cookie('csrftoken');
}

function csrf_token_string()
{
    return "<input type='hidden' name='csrfmiddlewaretoken' value='" + $j.cookie('csrftoken') + "' />";
}

function add_csrf_token()
{
    document.write(csrf_token_string());
}

function set_onsubmit()
{
    console.log("set_onsubmit");
    console.log($j("form[method=post]"));
    $j("form[method=post]").submit(function() { return check_csrf_cookie(this); });
}

function refresh_csrf_cookie()
{
    if (!$j.cookie('csrftoken'))
    {
        $j.ajax("/set_csrf_token", { async: false });
    }
}

function force_refresh_csrf_cookie()
{
    $j.ajax("/set_csrf_token", { async: false });
}

$j(document).ready(function() {
    $j.getScript("/media/scripts/csrf_check.js", set_onsubmit);
});
