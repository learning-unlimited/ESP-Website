
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
