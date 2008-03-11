/* Get user data from the cookies. */


if (typeof(window["$"]) == "undefined") {
    alert("JQuery and its cookie plugin are required for this page.");
    /* Hint:
       <script type="text/javascript" src="/media/scripts/jquery.js"></script>
       <script type="text/javascript" src="/media/scripts/jquery.cookie.js"></script>
    */
}

var esp_user = {};
var esp_user_keys = new Array('cur_username','cur_email','cur_first_name','cur_last_name','cur_other_user','cur_retTitle');

for (var i=0; i < esp_user_keys.length; i++) {
    var tmp = $.cookie(esp_user_keys[i]);
    if (tmp) {
	esp_user[esp_user_keys[i]] = tmp;
    }
}

var esp_user_login = null;

if (esp_user['cur_username']) {
    esp_user_login = '<table border="0" cellpadding="0" cellspacing="0" summary=" "><tr><td width="100%"><div class="divformcol1">&nbsp;</div></td><td style="text-align:left"><div class="divformcol1" style="text-align:left">';

    if (esp_user['cur_other_user'] == '1') {
	esp_user_login += '<a href="/myesp/switchback/">Go back to ' + esp_user['cur_retTitle'] + '</a>';
    } else {
	esp_user_login += 'Welcome, ' + esp_user['cur_first_name'] + '!';
    }
    esp_user_login += '</div></td><td colspan="2"><div class="divformcol2" style="text-align:right"><a href="/myesp/signout/">Sign Out</a></div></tr></table>';
}
