ESP = (function(){
  var loaded = false;
  var queued_modules = [];
  var adminbar = document.getElementById('adminbar_content');

  $j(document).ready(function() {
    loaded = true;
    for (var i = 0; i < queued_modules.length; i++)
    {
      ESP.registerAdminModule(queued_modules[i]);
    }
  });

  return {
    toggleDisplay: function(id) {
      var el = document.getElementById(id);
      if (el.style.display == "none") {
        el.style.display = "block";
      } else {
        el.style.display = "none";
      }
    },
    registerAdminModule: function(module) {
      if (loaded) {
        var module_wrap = document.createElement("div");
        var module_class = "adminbar_" + module.name;
        module_wrap.className = module_class;
        module_wrap.innerHTML =
	    "<div class='title' onclick='ESP.toggleDisplay(\""+module_class+"_content"+"\");'>" + module.name + "</div>";
        var module_content = document.createElement("div");
	module_content.id = module_class+"_content";
	module_content.className = "content";
        if (module.content_html) {
	    module_content.innerHTML = module.content_html;
	} else {
	    module_content.appendChild(document.getElementById(module.content_target));
	}
        module_wrap.appendChild(module_content);

        adminbar.appendChild(module_wrap);
      } else {
        queued_modules.push(module);
      }
    }
  };
})();

ESP.registerAdminModule({
content_html:
    '    <form id="user_search_form" name="user_search_form" method="get" action="/manage/usersearch">' +
    '      <input type="text" id="user_search_field" name="userstr" />' +
    '      <input type="submit" id="user_search_submit" name="search_submit" value="Find User"/>' +
    '    </form>',
    name: 'User Search'
    });

ESP.registerAdminModule({
    content_html: '    <a href="/themes/">Theme Settings</a><br /><a href="/admin/">DB Admin pages</a>',
    name: 'Links'
    });    
