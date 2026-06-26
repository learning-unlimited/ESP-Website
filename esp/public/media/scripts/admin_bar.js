// Default to empty array if theme template did not define toolbarLinks
if (typeof toolbarLinks === 'undefined') { var toolbarLinks = []; }
ESP = (function () {
  var loaded = false;
  var queued_modules = [];
  var adminbar = document.getElementById('adminbar_content');

  $j(document).ready(function () {
    loaded = true;
    for (var i = 0; i < queued_modules.length; i++) {        
      ESP.registerAdminModule(queued_modules[i]);
    }
  });

  return {
    toggleDisplay: function (id) {
      var el = document.getElementById(id);
      if (el.style.display == "none") {
        el.style.display = "block";
      } else {
        el.style.display = "none";
      }
    },
    registerAdminModule: function (module) {
      if (loaded) {
        var module_wrap = document.createElement("div");
        var module_class = "adminbar_" + module.name;
        module_wrap.className = module_class;
        module_wrap.innerHTML =
          "<div class='title' onclick='ESP.toggleDisplay(\"" + module_class + "_content" + "\");'>" + module.displayName + "</div>";
        var module_content = document.createElement("div");
        module_content.id = module_class + "_content";
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
    '<form id="usersearchform" name="usersearchform" method="get" action="/manage/usersearch">' +
    '<div class="input-group">' +
    '<input type="text" id="user_search_field" name="userstr" placeholder="Find User" class="form-control" />' +
    '<span class="input-group-btn">' +
    '<button type="submit" id="user_search_submit" name="search_submit" aria-label="Search" class="btn btn-secondary"><span class="bi bi-search bi-btn-height" aria-hidden="true"></span></button>' +
    '</span>' +
    '</div>' +
    '</form>',
  name: 'user_search',
  displayName: 'User Search'
});

if (currentPrograms && currentPrograms.forEach) {
  currentPrograms.forEach(function (currentProgram) {
    ESP.registerAdminModule({
      content_html:
        (currentProgram.class_search ? '<form id="class_search_form" name="class_search_form" method="get" action="/manage/' + currentProgram.urlBase + '/classsearch">' +
          '<div class="input-group">' +
          '<input type="text" id="class_search_field" name="namequery" placeholder="Find Class by Title" class="form-control" />' +
          '<span class="input-group-btn">' +
          '<button type="submit" id="class_search_submit" name="class_search_submit" aria-label="Search" class="btn btn-secondary"><span class="bi bi-search bi-btn-height" aria-hidden="true"></span></button>' +
          '</span>' +
          '</div>' +
          '</form>' : '') +
        '<div id="adminbar_Manage_content" class="content">' +
        '<a href="/manage/' + currentProgram.urlBase + '/main">Main Management Page</a><br />' +
        '<a href="/manage/' + currentProgram.urlBase + '/dashboard">Program Dashboard</a><br />' +
        '<a href="/onsite/' + currentProgram.urlBase + '/main">Main Onsite Page</a>' +
        '</div>',
      name: 'class_search',
      displayName: 'Manage ' + currentProgram.name
    });
  });
}

(function() {
    // Default hardcoded links -- never removed, only added to
    var linksHtml = '<a href="/manage/programs/">Manage all programs</a><br/>' +
                    '<a href="/manage/pages">Manage static pages</a><br />' +
                    (debug ? '<a href="/admin/">Administration pages</a><br />' : '') +
                    '<a href="/manage/site_media/">Manage media files</a><br />' +
                    '<a href="/themes/">Manage theme settings</a><br />' +
                    '<a href="/manage/docs/">Website Documentation</a>';

    // Append extra links configured in theme settings (never replaces defaults)
   if (Array.isArray(toolbarLinks) && toolbarLinks.length > 0) {
        toolbarLinks.forEach(function(link) {
            // Only allow relative URLs and http/https to prevent javascript:/data: XSS
            var url = link.link;
            if (url && (url.indexOf('/') === 0 || url.indexOf('http://') === 0 || url.indexOf('https://') === 0)) {
                var a = document.createElement('a');
                a.href = url;
                a.textContent = link.text;
                linksHtml += '<br/>' + a.outerHTML;
            }
        });
    }

    ESP.registerAdminModule({
        content_html: linksHtml,
        name: 'Other',
        displayName: 'Other Important Links'
    });
})();
