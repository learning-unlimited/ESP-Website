
function showEmailExplanation() {
    document.getElementById("from-help").style.display = '';
}

function hideEmailExplanation() {
    document.getElementById("from-help").style.display = 'none';
    document.getElementById("from").focus();
}


function validateMsgLang() {
  var msgTypes = document.getElementsByName("msglang");
  var containsTag = /<(\/?((.)|(br ?\/?)))>|(<img)/i.test(
    document.getElementById("emailbody").value);
  var containsHTag = /<\/?html>/i.test(
    document.getElementById("emailbody").value);

  if(containsHTag) {
      return confirm("Didn't we say not to include <html> tags?!? "
                + "If you're sure you know what you're doing, "
                + "click 'OK' to continue.");
  } else if(msgTypes[1].checked && !containsTag) {
      return confirm('You selected "HTML" but included no HTML tags. '
                + 'Continuing might squash your formatting. '
                + 'Would you still like to proceed?');
  } else if(msgTypes[0].checked && containsTag) {
      return confirm('You selected "Plain Text" but have HTML tags '
                + '(such as <p>) in your message. '
                + 'Continuing will leave your tags in your message '
                + '(so you would see "<b>hello</b>" instead of '
                + 'a bold "hello"). '
                + 'Would you still like to proceed?');
  }
  else {
      return true;
  }
}