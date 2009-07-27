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

var reset_forms = function()
{
    console.log("Registered forms: " + registered_forms);
    for (var i = 0; i < registered_forms.length; i++)
    {
        form = registered_forms[i];
        var theForm = dojo.byId(form.id);
        dojo.connect(theForm, "onsubmit", function (e) {handle_submit(form, e)});	
        console.log("Reset event handlers for form with attributes: " + form);
    }
    //  Try refetching fragments also, in case they changed due to a form action?
    //  fetch_fragments();
}

var fetch_fragments = function()
{
    console.log("Fetching fragments: " + registered_fragments);
    for (var i = 0; i < registered_fragments.length; i++)
    {
        frag = registered_fragments[i];
        fetch_fragment(frag);
    }
}

var apply_fragment_changes = function(data)
{
    console.log("Applying fragment changes from data: " + data);

    // Parse the keys
    for (var key in data)
    {
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
    console.log("Handling submission of form with attributes: " + form);
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

var fetch_fragment = function(attrs)
{
    console.log("Fetching fragment with attributes: " + attrs);
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
    console.log('Registered Ajax form with attributes: ' + form_attrs);
}

var register_fragment = function(fragment_attrs)
{
    registered_fragments.push(fragment_attrs);
    console.log('Registered Ajax page fragement with attributes: ' + fragment_attrs);
}

dojo.addOnLoad(reset_forms); 
dojo.addOnLoad(fetch_fragments);
