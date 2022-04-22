$j(document).ready(function() {
    $j("#sortable1").sortable({
        containment: "#learn_mods",
        scroll: false,
        connectWith: "#sortable2",
        update: function(event, ui) {
            $j('#learn_req').val($j(this).sortable('toArray'));
        }
    });
    $j('#learn_req').val($j("#sortable1").sortable('toArray'));
    
    $j("#sortable2").sortable({
        containment: "#learn_mods",
        scroll: false,
        connectWith: "#sortable1",
        update: function(event, ui) {
            $j('#learn_not_req').val($j(this).sortable('toArray'));
        }
    });
    $j('#learn_not_req').val($j("#sortable2").sortable('toArray'));
    
    $j("#sortable3").sortable({
        containment: "#teach_mods",
        scroll: false,
        connectWith: "#sortable4",
        update: function(event, ui) {
            $j('#teach_req').val($j(this).sortable('toArray'));
        }
    });
    $j('#teach_req').val($j("#sortable3").sortable('toArray'));
    
    $j("#sortable4").sortable({
        containment: "#teach_mods",
        scroll: false,
        connectWith: "#sortable3",
        update: function(event, ui) {
            $j('#teach_not_req').val($j(this).sortable('toArray'));
        }
    });
    $j('#teach_not_req').val($j("#sortable4").sortable('toArray'));
    
    $j(".connectedSortable li").click(function() {
        if($j(this).children("input").val() === "") {
            $j(this).children("input").toggle();
        }
    });
    
    $j(".connectedSortable li input").click(function(event) {
        event.stopPropagation();
        // Do something
    });
});
