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
  document.write('<style type="text/css"><!--\n' +
    '.dspcont{display:block;}\n' +
    '//--></style>');
}
