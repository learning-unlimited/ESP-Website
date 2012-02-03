
var data_fetch_status = Object();
var data = Object();

function check_json_status(components)
{
    if (components != null)
    {
        for (var i in components)
        {
            var key = components[i];
            if (data_fetch_status[key] != "Ready")
                return false;
        }
    }
    else for (var key in data_fetch_status)
    {
        if (data_fetch_status[key] != "Ready")
            return false;
    }
    return true;
}

function handle_json_response(new_data, text_status, jqxhr)
{
    console.log("Handling JSON response");
    
    //  Update data
    for (var key in new_data)
    {
        if (data.hasOwnProperty(key))
        {
            //  Update existing dictionary
            
            console.log("Updated data dictionary " + key);
        }
        else
        {
            //  Create new dictionary
            data[key] = {};
            for (var index in new_data[key])
            {
                var item = new_data[key][index];
                data[key][item.id] = item;
            }
            console.log("Created new data dictionary " + key);
        }
    }
    
    //  Set flags
    console.log("JQXHR is: " + jqxhr);
}

function json_fetch(components)
{
    for (var i in components)
    {
        data_fetch_status[components[i]] = "Waiting";
        $j.ajax({
            url: program_base_url + components[i],
            success: handle_json_response
        });
    }
    console.log(data_fetch_status);
    json_fetch_complete(components);
}

function json_fetch_complete(components)
{
    if (check_json_status(components))
    {
        console.log("All fetches complete");
    }
    else
    {
        setTimeout(function (){json_fetch_complete(components)}, 100);
    }
}

function init_jstest()
{
    data_components = [
        'rooms_status',
        'counts_status',
        //  'lottery_preferences'
    ];
    data = json_fetch(data_components);
}

$j(document).ready(init_jstest);


