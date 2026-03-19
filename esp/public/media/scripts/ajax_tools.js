'use strict';

//  ESP Ajax tools

//  Current tools include:
//  - Handle background submission of forms
//  - Handle responses that rewrite DOM nodes by supplying a key of [NODENAME]_html in JSON

//  Define an array for registered forms if they do not exist
window.registered_forms = window.registered_forms || [];
window.registered_fragments = window.registered_fragments || [];
window.registered_links = window.registered_links || [];

const reset_forms = function()
{
    //  Register forms
    //  console.log("Registered forms: " + JSON.stringify(registered_forms, null, '\t'));
    for (let i = 0; i < window.registered_forms.length; i++)
    {
        const form = window.registered_forms[i];
	      const formId = '#' + form.id;
	      const theForm = $j(formId);
        if (theForm.length > 0)
        {
	          // Clear existing connections
	          theForm.unbind('submit');
	          // Rebind the connection
	          theForm.submit(window.registered_forms[i].callback);
        }
    }
    
    //  Register links
    //  console.log("Registered links: " + JSON.stringify(registered_links, null, '\t'));
    for (let i = 0; i < window.registered_links.length; i++)
    {
        const link = window.registered_links[i];
	      const linkId = '#' + link.id;
        const theLink = $j(linkId);
        if (theLink.length > 0)
        {
            //  Clear existing connections
	          theLink.unbind('click');
	          //  Rebind the connection
	          theLink.click(window.registered_links[i].callback);
        }
    }    
    
    //  Try refetching fragments also, in case they changed due to a form action?
    //  fetch_fragments();
}

const fetch_fragments = function()
{
    //  console.log("Fetching fragments: " + JSON.stringify(registered_fragments, null, '\t'));
    for (let i = 0; i < window.registered_fragments.length; i++)
    {
        const frag = window.registered_fragments[i];
        fetch_fragment(frag);
    }
}

const apply_fragment_changes = function(data)
{
    //  console.log("Applying fragment changes from data: " + data);

    // Parse the keys
    for (const key in data)
    {
        //  Check for FOO_html ending, which means "replace HTML content of DOM node FOO"
        const re_match = key.match("([A-Za-z0-9_]*)_html");
        if (re_match)
        {
            //  console.log("Found match: " + re_match[1]);
	          const matchId = '#' + re_match[1];
            const matching_node = $j(matchId);
            if (matching_node.length > 0)
            {
                //  console.log("Rewriting HTML for element: " + re_match[1])
                matching_node.html(data[key]);
            }
        }
        
        if (key == 'script')
        {
            //  console.log("Evaluating: " + data[key]);
            //  SECURITY RISK: Executing arbitrary scripts from the server via JSON inherently poses XSS risks.
            //  Refactored to use new Function() which is marginally safer than eval() as it isolates execution
            //  to the global scope avoiding local variable leaks, but it still executes arbitrary code.
            new Function(data[key])();
        }
    }
}

const handle_success = function(data, textStatus, jqXHR)
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

const handle_submit = function(mode, attrs, eventObject)
{
    //  Check the csrf cookie and reject the submission if it fails
    //  Providing fallback 'this' for jQuery strict mode compliance which yields undefined over window
    const dynamicThis = this === undefined ? window : this;
    if($j(dynamicThis).length > 0 && typeof check_csrf_cookie !== 'undefined' && !check_csrf_cookie($j(dynamicThis)))
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



const fetch_fragment = function(attrs)
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

const register_form = function(form_attrs)
{
    const new_attrs = new CallbackForm(form_attrs.id, form_attrs.url);
    window.registered_forms.push(new_attrs);
    //  console.log('Registered Ajax form with attributes: ' + JSON.stringify(new_attrs, null, '\t'));
}

const register_link = function(link_attrs)
{
    const new_attrs = new CallbackLink(link_attrs.id, link_attrs.url, link_attrs.content, link_attrs.post_form);
    window.registered_links.push(new_attrs);
    //  console.log('Registered Ajax link with attributes: ' + JSON.stringify(new_attrs, null, '\t'));
}

const register_fragment = function(fragment_attrs)
{
    window.registered_fragments.push(fragment_attrs);
    //  console.log('Registered Ajax page fragment with attributes: ' + JSON.stringify(fragment_attrs, null, '\t'));
}

// Emplace globals dynamically explicitly to window, preserving interoperability with `<script>` tags externally bypassing const module scope limits.
window.register_form = register_form;
window.register_link = register_link;
window.register_fragment = register_fragment;

$j(document).ready(function()
{
    reset_forms();
    fetch_fragments();
});