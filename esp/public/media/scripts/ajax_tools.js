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
    console.log("Registered forms: " + JSON.stringify(registered_forms, null, '\t'));
    for (var i = 0; i < registered_forms.length; i++)
    {
        form = registered_forms[i];
        var theForm = dojo.byId(form.id);
        if (theForm)
        {
            //  Clear existing connections
            if (typeof theForm._connectHandler != "undefined")
            {
                dojo.disconnect(theForm._connectHandler);
            }
            theForm._connectHandler = dojo.connect(theForm, "onsubmit", function (e) {handle_submit(form, e)});
            //  console.log("Reset event handlers for form " + JSON.stringify(theForm, null, '\t') + " with attributes: " + JSON.stringify(form, null, '\t'));
        }
    }
    
    //  Register links
    console.log("Registered links: " + JSON.stringify(registered_links, null, '\t'));
    for (var i = 0; i < registered_links.length; i++)
    {
        link = registered_links[i];
        var theLink = dojo.byId(link.id);
        if (theLink)
        {
            //  Clear existing connections
            if (typeof theLink._connectHandler != "undefined")
            {
                dojo.disconnect(theLink._connectHandler);
            }
            theLink._connectHandler = dojo.connect(theLink, "onclick", function (e) {handle_link(link, e)});	
            //  console.log("Reset event handlers for link " + JSON.stringify(theLink, null, '\t') + " with attributes: " + JSON.stringify(link , null, '\t'));
        }
    }    
    
    //  Try refetching fragments also, in case they changed due to a form action?
    //  fetch_fragments();
}

var fetch_fragments = function()
{
    console.log("Fetching fragments: " + JSON.stringify(registered_fragments, null, '\t'));
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
            console.log("Evaluating: " + data[key]);
            eval(data[key]);
        }
        //  Check for FOO_html ending, which means "replace HTML content of DOM node FOO"
        var re_match = key.match("([A-Za-z0-9_]*)_html");
        if (re_match)
        {
            console.log("Found match: " + re_match[1]);
            matching_node = dojo.byId(re_match[1])
            if (matching_node)
            {
                console.log("Rewriting HTML for element: " + re_match[1])
                matching_node.innerHTML = data[key];
            }
        }
        
    }
}

var handle_submit = function(attrs, element)
{
    element.preventDefault(); 
    console.log("Handling submission of form with attributes: " + JSON.stringify(attrs, null, '\t') + ", element: " + JSON.stringify(element, null, '\t'));
    dojo.xhrPost({
        url: attrs.url,
        form: attrs.id,
        handleAs: "json",
        handle: function(data,args){
            if (typeof data == "error")
            {
                console.warn("error!",args);
            }
            else
            {
                //  Update portions of the page determined by response
                apply_fragment_changes(data);
                //  Reset the form event functions so they can be used again
                reset_forms();
            }
        }
    });
}

var handle_link = function(attrs, element)
{
    element.preventDefault(); 
    console.log("Handling submission of link with attributes: " + JSON.stringify(attrs, null, '\t') + ", element: " + JSON.stringify(element, null, '\t'));
    dojo.xhrGet({
        url: attrs.url,
        link: attrs.id,
        handleAs: "json",
        handle: function(data,args){
            if (typeof data == "error")
            {
                console.warn("error!",args);
            }
            else
            {
                //  Update portions of the page determined by response
                apply_fragment_changes(data);
                //  Reset the form event functions so they can be used again
                reset_forms();
            }
        }
    });
}

var fetch_fragment = function(attrs)
{
    console.log("Fetching fragment with attributes: " + JSON.stringify(attrs, null, '\t'));
    dojo.xhrGet({
        url: attrs.url,
        handleAs: "json",
        handle: function(data,args){
            if (typeof data == "error")
            {
                console.warn("error!",args);
            }
            else
            {
                //  Update portions of the page determined by response
                apply_fragment_changes(data);
                //  Reset the form event functions so they can be used again
                reset_forms();
            }
        }
    });
}
    
var register_form = function(form_attrs)
{
    registered_forms.push(form_attrs);
    console.log('Registered Ajax form with attributes: ' + JSON.stringify(form_attrs, null, '\t'));
}

var register_link = function(link_attrs)
{
    registered_links.push(link_attrs);
    console.log('Registered Ajax link with attributes: ' + JSON.stringify(link_attrs, null, '\t'));
}

var register_fragment = function(fragment_attrs)
{
    registered_fragments.push(fragment_attrs);
    console.log('Registered Ajax page fragement with attributes: ' + JSON.stringify(fragment_attrs, null, '\t'));
}

dojo.addOnLoad(reset_forms); 
dojo.addOnLoad(fetch_fragments);
