/* Get user data from the cookies. */


if (typeof(window["$j"]) == "undefined") {
    alert("JQuery and its cookie plugin are required for this page.");
    /* Hint:
       <script type="text/javascript" src="/media/scripts/jquery.js"></script>
       <script type="text/javascript" src="/media/scripts/jquery.cookie.js"></script>
    */
}

var esp_user = {};
var esp_user_keys = new Array('cur_username','cur_userid','cur_email','cur_first_name','cur_last_name','cur_other_user','cur_retTitle', 'cur_admin','cur_yog','cur_grade','cur_roles','cur_qsd_bits');

for (var i=0; i < esp_user_keys.length; i++) {
    var tmp = $j.cookie(esp_user_keys[i]);
    if (tmp) {
	esp_user[esp_user_keys[i]] = tmp;
    }
    /* These cookies are escape for potential unicode.
     * : see esp/middleware/esperrormiddleware.py
     */
}
esp_user['cur_userid'] = parseInt(esp_user['cur_userid']);
esp_user['cur_email'] = unescape(esp_user['cur_email']);
esp_user['cur_first_name'] = unescape(esp_user['cur_first_name']);
esp_user['cur_last_name'] = unescape(esp_user['cur_last_name']);
esp_user['cur_yog'] = parseInt(esp_user['cur_yog']);
esp_user['cur_grade'] = parseInt(esp_user['cur_grade']);
if (esp_user['cur_roles']) {
    esp_user['cur_roles'] = unescape(esp_user['cur_roles']).split(',');
} else {
    esp_user['cur_roles'] = [];
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
