function show_hide_sidebar() {
    if (esp_user.cur_username != null) {
        $j("#main.resizable").removeClass("span12");
        $j("#main.resizable").addClass("span9");
        $j("#sidebar").removeClass("hidden");
        $j("#sidebar").addClass("span3");
    } else {
        $j("#sidebar").addClass("hidden");
        $j("#sidebar").removeClass("span3");
        $j("#main.resizable").removeClass("span9");
        $j("#main.resizable").addClass("span12");
    }
}

$j(document).ready(show_hide_sidebar);

/* ===== Collapsible Sidebar (ReadTheDocs-style) ===== */
(function ($) {
    'use strict';

    function normalisePath(path) {
        if (!path) return '';
        try {
            var url = new URL(path, window.location.origin);
            path = url.pathname;
        } catch (e) { }
        path = path.replace(/\/+$/, '').replace(/\/index\.html$/i, '');
        return path.toLowerCase() || '/';
    }

    $(function () {
        var $sidebars = $('.sidebar-collapsible');
        if (!$sidebars.length) return;

        var currentPath = normalisePath(window.location.pathname);

        $sidebars.each(function () {
            var $sidebar = $(this);

            // Detect active links
            $sidebar.find('.sidebar-section').each(function () {
                var $section = $(this);
                var $headerLink = $section.find('.sidebar-header-link');
                if ($headerLink.length && normalisePath($headerLink.attr('href')) === currentPath) {
                    $section.addClass('active-section expanded');
                    $section.find('.sidebar-children').show();
                    $section.find('.sidebar-toggle').attr('aria-expanded', 'true');
                }
                $section.find('.sidebar-child-item').each(function () {
                    var $a = $(this).find('a');
                    if (normalisePath($a.attr('href')) === currentPath) {
                        $(this).addClass('active');
                        $section.addClass('active-section expanded');
                        $section.find('.sidebar-children').show();
                        $section.find('.sidebar-toggle').attr('aria-expanded', 'true');
                    }
                });
            });

            // Toggle handlers
            $sidebar.find('.sidebar-section-header').on('click', function (e) {
                if ($(e.target).closest('.sidebar-header-link').length) return;
                e.preventDefault();
                var $section = $(this).closest('.sidebar-section');
                var expanding = !$section.hasClass('expanded');
                if (expanding) {
                    $section.addClass('expanded');
                    $section.find('.sidebar-children').slideDown(200);
                    $section.find('.sidebar-toggle').attr('aria-expanded', 'true');
                } else {
                    $section.removeClass('expanded');
                    $section.find('.sidebar-children').slideUp(200);
                    $section.find('.sidebar-toggle').attr('aria-expanded', 'false');
                }
            });
        });
    });
})(window.$j || window.jQuery);
