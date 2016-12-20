
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
$j('ul.nav li a[href="'+window.location.pathname+'"]').parent().addClass('active');
$j('ul.nav li a[href="'+window.location.pathname+'/"]').parent().addClass('active');

$j('.navbar-manage-contractible').hide();
$j('.navbar-manage-expander').click(function () {
  $j('.navbar-manage-contractible').toggle();
});
