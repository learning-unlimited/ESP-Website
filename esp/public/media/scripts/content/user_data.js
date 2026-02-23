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

function decode_user_cookie(value) {
    if (value === undefined || value === null || value === '' || value === 'undefined' || value === 'null') {
        return '';
    }
    return unescape(value);
}

for (var i=0; i < esp_user_keys.length; i++) {
    var tmp = $j.cookie(esp_user_keys[i]);
    if (tmp) {
	esp_user[esp_user_keys[i]] = tmp;
    }
    /* These cookies are escape for potential unicode.
     * : see esp/middleware/esperrormiddleware.py
     */
}

esp_user['cur_userid'] = parseInt(esp_user['cur_userid'], 10);
esp_user['cur_yog'] = parseInt(esp_user['cur_yog'], 10);
esp_user['cur_grade'] = parseInt(esp_user['cur_grade'], 10);
if (isNaN(esp_user['cur_userid'])) { esp_user['cur_userid'] = null; }
if (isNaN(esp_user['cur_yog'])) { esp_user['cur_yog'] = null; }
if (isNaN(esp_user['cur_grade'])) { esp_user['cur_grade'] = null; }

esp_user['cur_email'] = decode_user_cookie(esp_user['cur_email']);
esp_user['cur_first_name'] = decode_user_cookie(esp_user['cur_first_name']);
esp_user['cur_last_name'] = decode_user_cookie(esp_user['cur_last_name']);
esp_user['cur_retTitle'] = decode_user_cookie(esp_user['cur_retTitle']);

if (esp_user['cur_roles']) {
    var decoded_roles = decode_user_cookie(esp_user['cur_roles']);
    esp_user['cur_roles'] = decoded_roles ? decoded_roles.split(',') : [];
} else {
    esp_user['cur_roles'] = [];
}

var esp_user_login = null;

if (esp_user['cur_username']) {
    esp_user_login = '<table border="0" cellpadding="0" cellspacing="0" summary=" "><tr><td width="100%"><div class="divformcol1">&nbsp;</div></td><td style="text-align:left"><div class="divformcol1" style="text-align:left">';

    if (esp_user['cur_other_user'] == '1') {
	esp_user_login += '<a href="/myesp/switchback/">Go back to ' + esp_user['cur_retTitle'] + '</a>';
    } else {
        var welcome_name = esp_user['cur_first_name'] || esp_user['cur_username'] || 'Guest';
	esp_user_login += 'Welcome, ' + welcome_name + '!';
    }
    esp_user_login += '</div></td><td colspan="2"><div class="divformcol2" style="text-align:right"><a href="/myesp/signout/">Sign Out</a></div></tr></table>';
}
