/*  Javascript code for generic2 theme UI
    So far this just handles switching between the secondary nav links
    to be displayed.
*/

var primary_divs = [];
var secondary_divs = [];

var primary_to_secondary = function(primary_div)
{
    for (var i = 0; i < primary_divs.length; i++)
    {
        if (primary_div == primary_divs[i])
            return $j('div.sublink:eq(' + i + ')');
    }
    //  console.log("Could not find secondary div matching " + primary_div);
}

var make_active = function(event)
{
    for (var i = 0; i < primary_divs.length; i++)
    {
        secondary_div = $j('div.sublink:eq(' + i + ')');
        secondary_div.addClass("sublink_hidden");
    }
    primary_to_secondary(event.currentTarget).removeClass("sublink_hidden");
}

var make_inactive = function(index)
{
    /*  Do nothing... this would have to be fairly intelligent to do what we want,
        which is to revert to the focused primary nav link only once you've also 
        moved your mouse out of the secondary link area.    
    */
}

var setup_nav = function() {

    //  Get primary and secondary navigation items
    primary_divs = $j('div.toplevel_link');
    secondary_divs = $j('div.sublink');
    
    //  Set callbacks for the primary navigation items
    for (var i = 0; i < primary_divs.length; i++)
    {
        primary_div = $j('div.toplevel_link:eq(' + i + ')');
        primary_div.hover(function (event) {make_active(event);}, function (event) {make_inactive(i);});
    }
    
    //  Hide all secondary navigation items except those for the primary one that has focus
    secondary_divs.addClass("sublink_hidden");
    if ($j('div.toplevel_focus').length > 0)
        primary_to_secondary($j('div.toplevel_focus')[0]).removeClass("sublink_hidden");
}

var setup_announcement_box = function() {
    $j('#new_announcement_box').click(function (event) {$j('#inner_announcement_box').toggleClass('box_hidden');});
}

var combined_setup = function() {
    setup_nav();
    setup_announcement_box();
}

$j(document).ready(combined_setup);
