'use strict';

//  Entry points other scripts and inline page scripts call by name.
/* exported register_handler, register_form, register_link, register_fragment, apply_fragment_changes */

//  ESP Ajax tools

//  Current tools include:
//  - Handle background submission of forms
//  - Handle responses that rewrite DOM nodes by supplying a key of [NODENAME]_html in JSON
//  - Handle responses that re-register forms and links, or invoke a callback the
//    page has registered by name, by supplying "forms", "links" or "callbacks"
//    keys in JSON.  Responses may not supply JavaScript to be executed.

//  Nothing at the top level of this file is declared with const or let: a page
//  may pull the script in more than once (see load_ajax_scripts.html), and a
//  second load would then fail with "identifier has already been declared".
//  Function declarations are safe to repeat (and stay reachable as window
//  properties for the inline page scripts that call them), and the registries
//  hang off window so that both loads share one set, which is what the previous
//  `if (!registered_forms) { var ... }` guard achieved through var hoisting.
window.registered_forms = window.registered_forms || [];
window.registered_fragments = window.registered_fragments || [];
window.registered_links = window.registered_links || [];
//  Null prototype, so handler names are only ever plain data keys.
window.registered_handlers = window.registered_handlers || Object.create(null);

//  Register a callback that Ajax responses are allowed to invoke by name.
function register_handler(name, callback)
{
    window.registered_handlers[name] = callback;
}

function reset_forms()
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
            theForm.submit(form.callback);
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
            theLink.click(link.callback);
        }
    }

    //  Try refetching fragments also, in case they changed due to a form action?
    //  fetch_fragments();
}

function fetch_fragments()
{
    //  console.log("Fetching fragments: " + JSON.stringify(registered_fragments, null, '\t'));
    for (let i = 0; i < window.registered_fragments.length; i++)
    {
        const frag = window.registered_fragments[i];
        fetch_fragment(frag);
    }
}

function apply_fragment_changes(data)
{
    //  console.log("Applying fragment changes from data: " + data);

    //  Response keys are honored only as own properties, so a polluted
    //  Object.prototype cannot inject them.
    const has_own_property = Object.prototype.hasOwnProperty;

    //  Rewrite DOM nodes first, so that anything registered below is applied to
    //  the markup that came with this response rather than the markup it replaces.
    for (const key in data)
    {
        if (!has_own_property.call(data, key)) { continue; }
        //  Check for exactly FOO_html, which means "replace HTML content of DOM node FOO"
        const re_match = key.match(/^([A-Za-z0-9_]+)_html$/);
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
    }

    //  Re-register forms and links found in the new markup.  These are bound by
    //  the reset_forms() call in handle_success().
    if (has_own_property.call(data, 'forms'))
    {
        for (let i = 0; i < data['forms'].length; i++)
        {
            register_form(data['forms'][i]);
        }
    }
    if (has_own_property.call(data, 'links'))
    {
        for (let i = 0; i < data['links'].length; i++)
        {
            register_link(data['links'][i]);
        }
    }

    //  Run the page callbacks that the response asked for.
    if (has_own_property.call(data, 'callbacks'))
    {
        for (let i = 0; i < data['callbacks'].length; i++)
        {
            //  A malformed entry is skipped rather than aborting the whole update.
            const requested = data['callbacks'][i] || {};
            const handler_name = requested['name'];
            if (typeof handler_name !== 'string' ||
                !has_own_property.call(window.registered_handlers, handler_name))
            {
                if (window.console)
                {
                    console.error("Ajax response requested an unregistered handler: " + handler_name);
                }
                continue;
            }
            const handler_args = requested['args'];
            window.registered_handlers[handler_name].apply(
                null, Array.isArray(handler_args) ? handler_args : []);
        }
    }

    if (has_own_property.call(data, 'script'))
    {
        if (window.console)
        {
            console.error("Ignoring 'script' key in Ajax response; server-supplied JavaScript is no longer executed.");
        }
    }
}

function handle_success(data)
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

function handle_submit(mode, attrs, _eventObject)
{
    //  jQuery invokes the CallbackForm/CallbackLink callback with `this` bound to
    //  the element the handler is on, and that callback passes it through as
    //  `attrs`.  Read the element from `attrs` rather than from `this`: under
    //  'use strict' a plain call leaves `this` undefined, where the old
    //  non-strict code silently got `window` and checked that instead.
    if (attrs && !check_csrf_cookie(attrs))
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

function fetch_fragment(attrs)
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

//  Replace any existing registration with the same ID.
function replace_registration(registrations, new_attrs)
{
    for (let i = 0; i < registrations.length; i++)
    {
        if (registrations[i].id === new_attrs.id)
        {
            registrations[i] = new_attrs;
            return;
        }
    }
    registrations.push(new_attrs);
}

function register_form(form_attrs)
{
    const new_attrs = new CallbackForm(form_attrs.id, form_attrs.url);
    replace_registration(window.registered_forms, new_attrs);
    //  console.log('Registered Ajax form with attributes: ' + JSON.stringify(new_attrs, null, '\t'));
}

function register_link(link_attrs)
{
    const new_attrs = new CallbackLink(link_attrs.id, link_attrs.url, link_attrs.content, link_attrs.post_form);
    replace_registration(window.registered_links, new_attrs);
    //  console.log('Registered Ajax link with attributes: ' + JSON.stringify(new_attrs, null, '\t'));
}

function register_fragment(fragment_attrs)
{
    window.registered_fragments.push(fragment_attrs);
    //  console.log('Registered Ajax page fragment with attributes: ' + JSON.stringify(fragment_attrs, null, '\t'));
}

$j(document).ready(function()
{
    reset_forms();
    fetch_fragments();
});
