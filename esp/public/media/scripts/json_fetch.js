
function check_json_status(components, data_fetch_status)
{
    if (components != null)
    {
        for (var i in components)
        {
	    // Handle prototype issues
	    if (typeof components[i] === 'function') {continue;}

            var key = components[i];
            if (data_fetch_status[key] != "Ready")
            {
                //  console.log("Not ready: " + key);
                return false;
            }
        }
    }
    else for (var key in data_fetch_status)
    {
        if (data_fetch_status[key] != "Ready")
        {
            //  console.log("Not ready: " + key);
            return false;
        }
    }
    return true;
}

function handle_json_response(data, component, data_fetch_status, new_data, text_status, jqxhr)
{
    //  Update data
    for (var key in new_data)
    {
        if (!data.hasOwnProperty(key))
            data[key] = {};

        for (var index in new_data[key])
        {
	    // Handle prototype issues
	    if (typeof new_data[key][index] === 'function') {continue}
            var item = new_data[key][index];
            if (data[key].hasOwnProperty(item.id))
            {
                for (var attr in item)
                {
                    data[key][item.id][attr] = item[attr];
                }
            }
            else
            {
                data[key][item.id] = item;
            }
        }
        
        //  console.log("Updated data dictionary " + key);
    }
    
    //  Set flags
    //  console.log("Setting to ready: " + component);
    if(component){
	data_fetch_status[component] = "Ready";
    }
}

function json_fetch(components, on_complete, result_data, on_error)
{
    var data_fetch_status = Object();
    if (!result_data)
    {
        result_data = Object();
        //  console.log("Initialized result data to empty object");
    }
    for (var i in components)
    {
	// Handle prototype issues
	if (typeof components[i] === 'function') { continue; }
        data_fetch_status[components[i]] = "Waiting";
        //  The 'with' statement creates new variables named 'component' which are properly scoped
        //  so that the handle_json_response() calls see the correct values.
        with ({component: components[i]})
        {
            $j.ajax({
                url: program_base_url + components[i],
                success: function(new_data, text_status, jqxhr) {handle_json_response(result_data, component, data_fetch_status, new_data, text_status, jqxhr);},
                error: on_error
            });
        }
    }
    return json_fetch_complete(components, on_complete, result_data, data_fetch_status);
}

function json_fetch_complete(components, on_complete, data, data_fetch_status)
{
    if (check_json_status(components, data_fetch_status))
    {
        //  console.log("Completed fetch of: " + components);
        on_complete(data);
    }
    else
    {
        setTimeout(function (){json_fetch_complete(components, on_complete, data, data_fetch_status);}, 100);
    }
}

function json_get(json_view, args, on_success, on_error)
{
    $j.ajax({
        url: program_base_url + json_view,
	data: args,
        success: function(result_data, text_status, jqxhr) {
	    final_data = {};
	    handle_json_response(final_data, null, null, result_data, text_status, jqxhr);
	    on_success(final_data);
	},
	error: on_error
    });
}
