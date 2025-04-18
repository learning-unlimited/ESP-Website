$j(function () {
    $j("#student_format").on("change", function (){
        // Get user-selected options
        var url = "./studentschedules/" + $j("#student_format").val() + "/?recipient_type=Student&base_list=enrolled";
        
        // Update href
        $j("#student_schedules a").attr('href', url);
    });
    
    $j("#schedule_user_type").on("change", function (){
        // Get user-selected options
        var url = "./" + $j("#schedule_user_type").val() + "?" + $j("#schedule_user_type option:selected").data("get");
        
        // Update href
        $j("#other_schedules a").attr('href', url);
    });
    
    $j("#class_list_options :input").on("change", function (){
        // Get user-selected options
        var fields = $j("#class_list_options :input");
        var get = "";
        // Create GET string
        fields.each(function (index, element) {
            var val = $j(this).val();
            if (val != "") {
                if (get != "" & get.charAt(get.length - 1) != "&") {
                    get += "&";
                }
                get += val;
            }
        });
        // Add GET string to all links
        $j("#class_lists a").each(function (){
            var base_url = $j(this).attr('href').split('?')[0];
            $j(this).attr('href', base_url + "?" + get)
        });
    });
    
    $j("#teacher_list_options :input").on("change", function (){
        // Get user-selected options
        var url = "./" + $j("#user_type").val() + "/";
        url += $j("#day_type").val();
        url += $j("#output_type").val();
        url += "?" + $j("#user_type option:selected").data("get");
        
        // Update href
        $j("#teacher_list a").attr('href', url);
    });
    
    $j("#item_type").on("change", function (){
        // Get user-selected options
        var url = "./selectList?recipient_type=Student&base_list=extracosts_" + $j("#item_type").val();
        
        // Update href
        $j("#line_item_list a").attr('href', url);
    });
});