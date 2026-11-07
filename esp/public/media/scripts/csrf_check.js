var CSRF_ALERT_MESSAGE = 'It appears your session has become disconnected. Please make sure cookies are enabled and try again.';

//  Show the "session disconnected" warning.  Most pages inherit the modal from
//  elements/html, but a few (the onsite webapps and the Django admin) are built
//  on their own skeletons without Bootstrap, so fall back to a plain alert there.
function showCsrfAlert()
{
    var el = document.getElementById('csrf-alert-modal');
    if (el && window.bootstrap)
    {
        bootstrap.Modal.getOrCreateInstance(el).show();
    }
    else
    {
        alert(CSRF_ALERT_MESSAGE);
    }
}

function strip_tags(str)
{
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt");
}

var check_csrf_cookie = function(form)
{
    //console.log("CSRF check!");
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

    //Refresh the csrf token if needed
    refresh_csrf_cookie();

    //If this form is missing the csrfmiddlewaretoken, add it
    if (!form.csrfmiddlewaretoken)
    {
        //  console.log('Missing csrfmiddlewaretoken, adding');
        $j(form).append(csrf_token_string());
    }

    //Check it
    var csrf_token = $j(form.csrfmiddlewaretoken).val();
    //  console.log(csrf_token);
    csrf_cookie = $j.cookie("esp_csrftoken");
    if (csrf_cookie == null)
    {
        showCsrfAlert();
        return false;
    }

    if (csrf_cookie != $j(form.csrfmiddlewaretoken).val())
    {
        //  console.log('Not matching. csrf_cookie: ' + csrf_cookie + ', csrfmiddlewaretoken: ' + csrf_token);
    }
    return true;
}
