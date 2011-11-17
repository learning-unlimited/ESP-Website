$j.getScript("/media/scripts/csrf_check.js", set_onsubmit);

function set_onsubmit()
{ 
  //Select all forms
  $j("form").submit(function() { return check_csrf_cookie(this); });
}

var csrfmiddlewaretoken = $j.cookie("csrftoken");
if (csrfmiddlewaretoken == "")
{
  //Block on this because it's a small view and not having the cookie
  //set before the rest of the page loads would not resolve the issue
  $j.ajax("/set_csrf_token", {asyc: false});
}

function csrftoken() {
  document.write("<input type='hidden' name='csrfmiddlewaretoken' value='" + csrfmiddlewaretoken + "' />");
}
