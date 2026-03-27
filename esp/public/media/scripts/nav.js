
//set the correct hrefs for the links on the sidebar depending on user type

$j('#side-home a').prop('href', function() {
    if ($j.inArray("Student", esp_user.cur_roles) != -1) 
	return '/learn/index.html';
});

$j('#side-dashboard a').prop('href', function() {
    if ($j.inArray("Administrator", esp_user.cur_roles) != -1) 
	return '/manage/programs/';
});

//Select the appropriate nav-list <li> that contains an <a> which points to the current 
//page, and make it active.
function highlightNavLink() {
  const path = window.location.pathname
  let candidateUrls = [
    path, // standard path
    path + "/" // adds trailing slash
  ]
  if (path.endsWith("index.html")) {
    candidateUrls.push(
      path.slice(0, -10), // remove "index.html"
      path.slice(0, -11) // remove "/index.html"
    )
  }
  
  candidateUrls.forEach((url)=>{
    let elem = document.querySelector(`ul.nav li a[href="${url}"]`)
    if (elem) elem.parentElement.classList.add("active")
  })
}

highlightNavLink()

$j('.navbar-manage-contractible').hide();
$j('.navbar-manage-expander').on("click", function () {
  $j('.navbar-manage-contractible').toggle();
});

/* ===== Collapsible Sidebar for navbar_left submenu (ReadTheDocs-style) ===== */
(function ($) {
  'use strict';

  function normalisePath(path) {
    if (!path) return '';
    try { path = new URL(path, window.location.origin).pathname; } catch (e) { }
    return (path.replace(/\/+$/, '').replace(/\/index\.html$/i, '') || '/').toLowerCase();
  }

  $(function () {
    var $submenu = $('ul#submenu.sidebar-collapsible');
    if (!$submenu.length) return;

    var currentPath = normalisePath(window.location.pathname);

    $submenu.find('.sidebar-section-header').each(function () {
      var $header = $(this);
      var $li = $header.closest('li');

      // Collect following indent siblings as children
      var $children = $li.nextUntil(':not(.indent)');
      if ($children.length) {
        var $wrapper = $('<ul class="sidebar-children" style="display: none;"></ul>');
        $children.each(function () {
          $(this).addClass('sidebar-child-item');
          $wrapper.append($(this));
        });
        $li.after($wrapper);

        // Check if any child is active
        var hasActive = false;
        $wrapper.find('a').each(function () {
          if (normalisePath($(this).attr('href')) === currentPath) {
            $(this).closest('li').addClass('active');
            hasActive = true;
          }
        });

        if (hasActive) {
          $li.addClass('active-section expanded');
          $wrapper.show();
          $li.find('.sidebar-toggle').attr('aria-expanded', 'true');
        }
      }

      // Toggle handler
      $header.on('click', function (e) {
        if ($(e.target).closest('a').length) return;
        e.preventDefault();
        var expanding = !$li.hasClass('expanded');
        var $childList = $li.next('.sidebar-children');
        if (expanding) {
          $li.addClass('expanded');
          $childList.slideDown(200);
          $li.find('.sidebar-toggle').attr('aria-expanded', 'true');
        } else {
          $li.removeClass('expanded');
          $childList.slideUp(200);
          $li.find('.sidebar-toggle').attr('aria-expanded', 'false');
        }
      });
    });
  });
})(window.$j || window.jQuery);
