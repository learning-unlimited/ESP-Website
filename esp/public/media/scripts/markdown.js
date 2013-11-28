
var media_url = '/media/';

function addWikiFormattingToolbar(jq) {

  var textarea = jq.get(0);

  
  /*var toolbar = document.createElement("div");
  toolbar.className = "wikitoolbar"; */
  
  jq.before('<div class="wikitoolbar"></div>');
  new_div = jq.parent().children("div.wikitoolbar");

  function addButton(id, title, fn) {
    new_div.append('<a href="#" title="'+title+'" id="'+id+'"></a>');
    new_a = new_div.children("#"+id);
    a = $j(new_a).get(0);
    a.onclick = function() { try { fn() } catch (e) { } return false };
    a.tabIndex = 400;
    new_a.append('<img src="'+media_url+'images/markdownbar/'+id+'.png" '
    +'border="0" alt="'+title+'" />');
 
  }

  function encloseSelection(prefix, suffix) {
    textarea.focus();
    var start, end, sel, scrollPos, subst;
    if (typeof(document["selection"]) != "undefined") {
      sel = document.selection.createRange().text;
    } else if (typeof(textarea["setSelectionRange"]) != "undefined") {
      start = textarea.selectionStart;
      end = textarea.selectionEnd;
      scrollPos = textarea.scrollTop;
      sel = textarea.value.substring(start, end);
    }
    if (sel.match(/ $/)) { // exclude ending space char, if any
      sel = sel.substring(0, sel.length - 1);
      suffix = suffix + " ";
    }
    subst = prefix + sel + suffix;
    if (typeof(document["selection"]) != "undefined") {
      var range = document.selection.createRange().text = subst;
      textarea.caretPos -= suffix.length;
    } else if (typeof(textarea["setSelectionRange"]) != "undefined") {
      textarea.value = textarea.value.substring(0, start) + subst +
                       textarea.value.substring(end);
      if (sel) {
        textarea.setSelectionRange(start + subst.length, start + subst.length);
      } else {
        textarea.setSelectionRange(start + prefix.length, start + prefix.length);
      }
      textarea.scrollTop = scrollPos;
    }
  }

  addButton("strong", "Bold text: **Example**", function() {
    encloseSelection("**", "**");
  });
  addButton("em", "Italic text: *Example*", function() {
    encloseSelection("*", "*");
  });
  addButton("heading", "Heading: # Example", function() {
    encloseSelection("", "\n=================\n", "Heading");
  });
  addButton("link", 'Link: [link](http://www.example.com/ "Example")', function() {
    encloseSelection("[", '](http://example.com "Title")');
  });
  addButton("hr", "Horizontal rule: ----", function() {
    encloseSelection("\n-------------------------------\n", "");
  });
  addButton("np", "New paragraph", function() {
    encloseSelection("\n\n", "");
  });
  addButton("br", "Line break: <br />", function() {
    encloseSelection("<br />\n", "");
  });
  addButton("latex_math", "LaTeX Math Symbols", function() {
      encloseSelection("$$ ", " $$");
  });
  addButton("upload", "Link to uploaded file", function() {
      encloseSelection("[link](qsdmedia/", "file.ext)");
  });
  addButton("image", "![Alt text](qsdmedia/img.jpg)", function() {
      encloseSelection("![Alt text](qsdmedia/", "img.ext)");
  });
  
//  textarea.parentNode.insertBefore(toolbar, textarea);
}


$j(document).ready(function() {
  $j("textarea.markdown").each( function(i) {
    addWikiFormattingToolbar($j(this));
  });

});

