function csrf_token()
{
    return $j.cookie('esp_csrftoken');
}

function csrf_token_string()
{
    return "<input type='hidden' name='csrfmiddlewaretoken' value='" + $j.cookie('esp_csrftoken') + "' />";
}

function add_csrf_token()
{
    document.write(csrf_token_string());
}

function set_onsubmit()
{
    $j("form[method=post]").submit(function() { return check_csrf_cookie(this); });
}

function refresh_csrf_cookie()
{
    if (!$j.cookie('esp_csrftoken'))
    {
        $j.ajax("/set_csrf_token", { async: false });
    }
}

function force_refresh_csrf_cookie()
{
    $j.ajax("/set_csrf_token", { async: false });
}

$j(document).ready(function() {
    $j.getScriptWithCaching("/media/scripts/csrf_check.js", set_onsubmit);
});
