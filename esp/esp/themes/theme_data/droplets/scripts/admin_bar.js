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
            "<div class='title'>" + module.displayName + "</div>";
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

// In Bootstrap 3, replace these with
// http://getbootstrap.com/components/#input-groups-buttons

ESP.registerAdminModule({
content_html:
    '<form id="usersearchform" name="usersearchform" method="get" action="/manage/usersearch">' +
    '<div class="input-append">' +
    '<input type="text" id="user_search_field" name="userstr" placeholder="Find User" />' +
    '<button type="submit" id="user_search_submit" name="search_submit" aria-label="Search" class="btn btn-default"><span class="glyphicon glyphicon-search glyphicon-btn-height" aria-hidden="true"></span></button>' +
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
                '<div class="input-append">' +
                '<input type="text" id="class_search_field" name="namequery" placeholder="Find Class by Title" />' +
                '<button type="submit" id="class_search_submit" name="class_search_submit" aria-label="Search" class="btn btn-default"><span class="glyphicon glyphicon-search glyphicon-btn-height" aria-hidden="true"></span></button>' +
                '</div>' +
                '</form>' : '') +
                '<div id="adminbar_Manage_content" class="content">' +
                '<a href="/manage/' + currentProgram.urlBase +'/main">Main Management Page</a><br />' +
                '<a href="/manage/' + currentProgram.urlBase +'/dashboard">Program Dashboard</a><br />' +
                '<a href="/onsite/' + currentProgram.urlBase +'/main">Main Onsite Page</a>' +
                '</div>',
            name: 'class_search',
            displayName: 'Manage ' + currentProgram.name
        });
    });
}

// Get admin_links from theme settings
var adminLinks = (window.theme_settings && window.theme_settings.admin_links) || [];

var contentHtml = '<div class="content">';

if (adminLinks.length > 0) {
    for (var i = 0; i < adminLinks.length; i++) {
        var linkObj = adminLinks[i];
        if (linkObj.text && linkObj.link) {
            contentHtml += '<a href="' + linkObj.link + '">' + linkObj.text + '</a><br />';
        }
    }
} else {
    // fallback (optional, safe)
    contentHtml += '<a href="/manage/programs/">Manage all programs</a><br />';
    contentHtml += '<a href="/manage/pages">Manage static pages</a><br />';
    if (debug) {
        contentHtml += '<a href="/admin/">Administration pages</a><br />';
    }
    contentHtml += '<a href="/admin/filebrowser/browse/">Manage media files</a><br />';
    contentHtml += '<a href="/themes/">Manage theme settings</a>';
}

contentHtml += '</div>';

ESP.registerAdminModule({ 
    content_html: contentHtml,
    name: 'Other', 
    displayName: 'Other Important Links' 
});
