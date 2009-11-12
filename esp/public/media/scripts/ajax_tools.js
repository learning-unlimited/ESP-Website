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
if (!connection_map)
{
    var connection_map = {};
}

var reset_forms = function()
{
    //  Register forms
    //  console.log("Registered forms: " + JSON.stringify(registered_forms, null, '\t'));
    for (var i = 0; i < registered_forms.length; i++)
    {
        form = registered_forms[i];
        var theForm = dojo.byId(form.id);
        if (theForm)
        {
            if (connection_map[form.id] != "undefined")
            {
                //  console.log("Disconnecting connection_map[" + form.id + "] =" + connection_map[form.id]);
                dojo.disconnect(connection_map[form.id]);
            }
            result = dojo.connect(theForm, "onsubmit", registered_forms[i], 'callback');
            //  console.log("Setting up callback for " + form.id + " to " + JSON.stringify(registered_forms[i], null, '\t'));
            connection_map[form.id] = result;
        }
    }
    
    //  Register links
    //  console.log("Registered links: " + JSON.stringify(registered_links, null, '\t'));
    for (var i = 0; i < registered_links.length; i++)
    {
        link = registered_links[i];
        var theLink = dojo.byId(link.id);
        if (theLink)
        {
            //  Clear existing connections
            if (connection_map[link.id] != "undefined")
            {
                dojo.disconnect(connection_map[link.id]);
            }
            result = dojo.connect(theLink, "onclick", registered_links[i], 'callback');
            //  console.log("Setting up callback for " + link.id + " to " + JSON.stringify(registered_links[i], null, '\t'));
            connection_map[link.id] = result;
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
        if (key == 'script')
        {
            //  console.log("Evaluating: " + data[key]);
            eval(data[key]);
        }
        //  Check for FOO_html ending, which means "replace HTML content of DOM node FOO"
        var re_match = key.match("([A-Za-z0-9_]*)_html");
        if (re_match)
        {
            //  console.log("Found match: " + re_match[1]);
            matching_node = dojo.byId(re_match[1])
            if (matching_node)
            {
                console.log("Rewriting HTML for element: " + re_match[1])
                matching_node.innerHTML = data[key];
            }
        }
        
    }
}

var dojo_handle = function(data,args)
{
    if (args.xhr.status != 200)
    {
        //  console.log("Received status = " + args.xhr.status + ", skipping handler.");
    }
    else
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
}

var handle_submit = function(mode, attrs, element)
{
    element.preventDefault(); 
    //  console.log("Handling " + mode + " submission of object: " + JSON.stringify(attrs, null, '\t') + ", element: " + JSON.stringify(element, null, '\t'));
    if (attrs.post_form != null)
    {
        attrs.form = attrs.post_form;
    }
    else
    {
        attrs.form = attrs.id;
    }
    params = {
        url: attrs.url,
        form: attrs.form,
        content: attrs.content,
        handleAs: "json",
        handle: dojo_handle,
    };
    if (mode == 'post')
    {
        dojo.xhrPost(params);
    }
    else
    {
        dojo.xhrGet(params);
    }
}



var fetch_fragment = function(attrs)
{
    //  console.log("Fetching fragment with attributes: " + JSON.stringify(attrs, null, '\t'));
    dojo.xhrGet({
        url: attrs.url,
        handleAs: "json",
        handle: dojo_handle
    });
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

dojo.addOnLoad(reset_forms); 
dojo.addOnLoad(fetch_fragments);
