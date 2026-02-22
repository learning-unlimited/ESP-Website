var coll = document.getElementsByClassName("dsphead");
var i;

for (i = 0; i < coll.length; i++) {
  coll[i].addEventListener("click", function() {
    this.classList.toggle("active");
    var content = this.nextElementSibling;
    content.classList.toggle("active");
    if (content.style.maxHeight){
      content.style.maxHeight = null;
    } else {
      content.style.maxHeight = "none";
    }
  });
}

var coll = document.getElementsByClassName("dspcont active");
var i;

for (i = 0; i < coll.length; i++) {
  coll[i].style.maxHeight = "none";
}

if(!document.getElementById) {
  // Legacy fallback: inject CSS without using document.write
  try {
    var style = document.createElement('style');
    style.type = 'text/css';
    if (style.styleSheet) { // IE
      style.styleSheet.cssText = '.dspcont{display:block;}';
    } else {
      style.appendChild(document.createTextNode('.dspcont{display:block;}'));
    }
    var head = document.getElementsByTagName('head')[0] || document.documentElement;
    head.appendChild(style);
  } catch (e) {
    // Silently ignore — non-critical fallback for very old browsers
  }
}