/*  Javascript code for generic2 theme UI
    So far this just handles switching between the secondary nav links
    to be displayed: on hover, on keyboard focus, and on a first tap on
    touch screens (which have no hover).
*/

var primary_divs = [];
var secondary_divs = [];
var tap_reveals_links = false;

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

/*  All the tabs come before all the link groups in the page, so Tab from a
    tab would reach the next tab (hiding this tab's links) before the links.
    These route Tab and Shift+Tab through tab 1, its links, tab 2, its links...
*/
var group_links = function(index)
{
    return $j('div.sublink:eq(' + index + ') > a');
}

var keyboard_into_links = function(event)
{
    if (event.key != 'Tab')
        return;
    var index = primary_divs.index($j(event.currentTarget).closest('div.toplevel_link'));
    if (!event.shiftKey && group_links(index).length > 0)
    {
        event.preventDefault();
        group_links(index).first().focus();
    }
    else if (event.shiftKey && index > 0 && group_links(index - 1).length > 0)
    {
        event.preventDefault();
        primary_divs.eq(index - 1).children('a').focus();
        group_links(index - 1).last().focus();
    }
}

var keyboard_out_of_links = function(event)
{
    if (event.key != 'Tab')
        return;
    var index = secondary_divs.index($j(event.currentTarget).closest('div.sublink'));
    var links = group_links(index);
    if (event.shiftKey && event.currentTarget == links.first()[0])
    {
        event.preventDefault();
        primary_divs.eq(index).children('a').focus();
    }
    else if (!event.shiftKey && event.currentTarget == links.last()[0] && index + 1 < primary_divs.length)
    {
        event.preventDefault();
        primary_divs.eq(index + 1).children('a').focus();
    }
}

var setup_nav = function() {

    //  Get primary and secondary navigation items
    primary_divs = $j('div.toplevel_link');
    secondary_divs = $j('div.sublink');
    
    //  Set callbacks for the primary navigation items
    for (var i = 0; i < primary_divs.length; i++)
    {
        primary_div = $j('div.toplevel_link:eq(' + i + ')');
        //  Hover only for a real mouse: touch browsers also send emulated
        //  mouse events, which would reveal the links before a tap is handled.
        primary_div.on('pointerenter', function (event) {
            if (event.originalEvent.pointerType == 'mouse')
                make_active(event);
        });
        primary_div.on('pointerleave', function (event) {make_inactive(i);});
        primary_div.on('focusin', function (event) {make_active(event);});
        primary_div.on('keydown', 'a', keyboard_into_links);

        //  Decide on pointerdown whether this tap should reveal the links
        //  instead of following the section's own link.
        primary_div.on('pointerdown', function (event) {
            var secondary_div = primary_to_secondary(event.currentTarget);
            tap_reveals_links = event.originalEvent.pointerType != 'mouse' &&
                secondary_div.hasClass("sublink_hidden") &&
                secondary_div.children('a').length > 0;
        });
        //  A touch that turns into a scroll never clicks.
        primary_div.on('pointercancel', function () {tap_reveals_links = false;});
        primary_div.on('click', function (event) {
            if (tap_reveals_links)
            {
                event.preventDefault();
                make_active(event);
            }
            tap_reveals_links = false;
        });
    }
    
    secondary_divs.on('keydown', 'a', keyboard_out_of_links);

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
