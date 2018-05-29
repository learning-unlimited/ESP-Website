function expand_disp(loc){
   if(document.getElementById){
      var sign = loc.firstChild.innerHTML ?
         loc.firstChild:
         loc.firstChild.nextSibling;
      var target = loc.parentNode.nextSibling.style ?
         loc.parentNode.nextSibling:
         loc.parentNode.nextSibling.nextSibling;
      if (target.style.display === 'none') {
        target.style.display = 'block';
        sign.innerHTML = '&minus;';
      } else {
        target.style.display = 'none';
        sign.innerHTML = '+';
      }
   }
}


if(!document.getElementById) {
  document.write('<style type="text/css"><!--\n' +
    '.dspcont{display:block;}\n' +
    '//--></style>');
}
