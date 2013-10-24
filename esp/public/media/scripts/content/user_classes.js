function update_user_classes() {
  if (esp_user.cur_admin == "1") {
    $j(".admin").removeClass("admin_hidden");
  }
  if (esp_user.cur_retTitle) {
    $j(".unmorph").removeClass("unmorph_hidden");
    $j("#unmorph_text").html("Click above to return to your administrator account - " + esp_user.cur_retTitle);
  }
  if (esp_user.cur_qsd_bits == "1") {
    $j(".qsd_bits").removeClass("qsd_bits_hidden");
  }
  if (esp_user.cur_username != null) {
    $j(".not_logged_in").addClass("not_logged_in_hidden");
    $j(".logged_in").removeClass("logged_in_hidden");
  }
  else {
    $j(".not_logged_in").removeClass("not_logged_in_hidden");
    $j(".logged_in").addClass("logged_in_hidden");
  }

  var type_name = '';
  var hidden_name = '';
  for (var i = 0; i < esp_user.cur_roles.length; i++) {
    type_name = "." + esp_user.cur_roles[i];
    hidden_name = esp_user.cur_roles[i] + "_hidden";
    $j(type_name).removeClass(hidden_name);
  }
  
  //    Write user's name in the appropriate spot in the login box
  $j("#loginbox_user_name").html("Hello, " + esp_user.cur_first_name + " " + esp_user.cur_last_name + "<br /><span style='color: #444; font-style: italic;'>" + esp_user.cur_username + " / " + esp_user.cur_userid + "</span>");
}
