$j(function(){
    function update_form() {
        var checkbox = document.getElementById("id_will_moderate");
        if(checkbox.checked){
            $j("#moderate_form tr").not(":first").not(":last").show();
        } else {
            $j("#moderate_form tr").not(":first").not(":last").hide();
            $j("#id_num_slots").val("0");
            $j("#id_class_categories").val([]);
            $j("#id_comments").val("");
        }
    }

    $j("#id_will_moderate").change(function() {
        update_form();
    });

    update_form();
});