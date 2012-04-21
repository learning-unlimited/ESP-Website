//  ESP Ajax tools

//  Current tools include:
//  - Handle background submission of forms
//  - Handle responses that rewrite DOM nodes by supplying a key of [NODENAME]_html in JSON

//  Define an array for registered forms if they do not exist
if (!registered_forms)
{
    var registered_forms = [];
}
if (!registered_fragments)
{
    var registered_fragments = [];
}
if (!registered_links)
{
    var registered_links = [];
}

var reset_forms = function()
{
    //  Register forms
    //  console.log("Registered forms: " + JSON.stringify(registered_forms, null, '\t'));
    for (var i = 0; i < registered_forms.length; i++)
    {
        form = registered_forms[i];
	var formId = '#' + form.id;
	var theForm = $j(formId);
        if (theForm.length > 0)
        {
	    // Clear existing connections
	    theForm.unbind('submit');
	    // Rebind the connection
	    theForm.submit(registered_forms[i].callback);
        }
    }
    
    //  Register links
    //  console.log("Registered links: " + JSON.stringify(registered_links, null, '\t'));
    for (var i = 0; i < registered_links.length; i++)
    {
        link = registered_links[i];
	var linkId = '#' + link.id;
        var theLink = $j(linkId);
        if (theLink.length > 0)
        {
            //  Clear existing connections
	    theLink.unbind('click');
	    //  Rebind the connection
	    theLink.click(registered_links[i].callback);
        }
    }    
    
    //  Try refetching fragments also, in case they changed due to a form action?
    //  fetch_fragments();
}

var fetch_fragments = function()
{
    //  console.log("Fetching fragments: " + JSON.stringify(registered_fragments, null, '\t'));
    for (var i = 0; i < registered_fragments.length; i++)
    {
        frag = registered_fragments[i];
        fetch_fragment(frag);
    }
}

var apply_fragment_changes = function(data)
{
    //  console.log("Applying fragment changes from data: " + data);

    // Parse the keys
    for (var key in data)
    {
        //  Check for FOO_html ending, which means "replace HTML content of DOM node FOO"
        var re_match = key.match("([A-Za-z0-9_]*)_html");
        if (re_match)
        {
            //  console.log("Found match: " + re_match[1]);
	    var matchId = '#' + re_match[1];
            matching_node = $j(matchId);
            if (matching_node.length > 0)
            {
                //  console.log("Rewriting HTML for element: " + re_match[1])
                matching_node.html(data[key]);
            }
        }
        
        if (key == 'script')
        {
            //  console.log("Evaluating: " + data[key]);
            eval(data[key]);
        }
    }
}

var handle_success = function(data, textStatus, jqXHR)
{
    if ('error' in data)
    {
        //  Maybe this should be something more gentle like a floating div.
        alert(data['error']);
        return;
    }   
    //  Update portions of the page determined by response
    apply_fragment_changes(data);
    //  Reset the form event functions so they can be used again
    reset_forms();
}

var handle_submit = function(mode, attrs, eventObject)
{
    //  Check the csrf cookie and reject the submission if it fails
    if($j(this).length > 0 && !check_csrf_cookie($j(this)))
    {
        return false;
    }

    if (attrs.post_form != null)
    {
        attrs.form = attrs.post_form;
    }
    else
    {
        attrs.form = attrs.id;
    }

    //  I'm not sure if these calls are correct -- test this
    if (mode == 'post')
    {
	$j.post(attrs.url, attrs.content, handle_success, "json");
    }
    else
    {
	$j.get(attrs.url, attrs.content, handle_success, "json");
    }
}



var fetch_fragment = function(attrs)
{
    //  console.log("Fetching fragment with attributes: " + JSON.stringify(attrs, null, '\t'));
    if (! attrs.url) { return; }
    $j.get(attrs.url, handle_success, "json");
}
    
function CallbackForm(id, url)
{
    this.id = id;
    this.url = url;
    this.callback = function (e) {handle_submit('post', this, e)};
}
    
function CallbackLink(id, url, content, post_form)
{
    this.id = id;
    this.url = url;
    this.content = content;
    this.post_form = post_form;
    if (this.post_form)
    {
        this.callback = function (e) {handle_submit('post', this, e)};
    }
    else
    {
        this.callback = function (e) {handle_submit('get', this, e)};
    }
}

var register_form = function(form_attrs)
{
    var new_attrs = new CallbackForm(form_attrs.id, form_attrs.url);
    registered_forms.push(new_attrs);
    //  console.log('Registered Ajax form with attributes: ' + JSON.stringify(new_attrs, null, '\t'));
}

var register_link = function(link_attrs)
{
    var new_attrs = new CallbackLink(link_attrs.id, link_attrs.url, link_attrs.content, link_attrs.post_form);
    registered_links.push(new_attrs);
    //  console.log('Registered Ajax link with attributes: ' + JSON.stringify(new_attrs, null, '\t'));
}

var register_fragment = function(fragment_attrs)
{
    registered_fragments.push(fragment_attrs);
    //  console.log('Registered Ajax page fragement with attributes: ' + JSON.stringify(fragment_attrs, null, '\t'));
}

$j(document).ready(function()
{
    reset_forms();
    fetch_fragments();
});