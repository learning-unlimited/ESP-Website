$j(function () {
    $j("#id_status").on('focusin', function(){
        $j(this).data('old_val', $j(this).val());
    });
    $j("#id_status").on("change", function() {
        if($j(this).val() == -20) {
            $j(this).val($j(this).data('old_val'));
            alert("This class has already been scheduled. Please use the cancellation form above to cancel the class.");
        }
        $j(this).data('old_val', $j(this).val());
    });
});

$j(function () {
    $j("[id$='-status']").on('focusin', function(){
        $j(this).data('old_val', $j(this).val());
    });
    $j("[id$='-status']").on("change", function() {
        if($j(this).val() == -20) {
            $j(this).val($j(this).data('old_val'));
            alert("This section has already been scheduled. Please use the cancellation form above to cancel the section.");
        }
        $j(this).data('old_val', $j(this).val());
    });
});
