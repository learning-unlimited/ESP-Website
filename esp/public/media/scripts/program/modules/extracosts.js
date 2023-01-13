var amount_paid = 0;
var amount_finaid = 0;
var amount_due = 0;
var prog_cost = 0;

$j(function() { 
    amount_paid = parseFloat($j("#amount_paid").data("total"));
    amount_finaid = parseFloat($j("#amount_finaid").data("total"));
    prog_cost = parseFloat($j("#amount_cost").data("total")) || 0;
    updateTotalCost();
    $j("input[name*='-cost']").on('change', updateTotalCost);
    $j("input[name*='-count']").on('change', updateTotalCost);
    $j("input[name*='-option']").on('change', updateTotalCost);
    $j("input[name*='-siblingdiscount']").on('change', updateTotalCost);
});

function updateTotalCost() {
    var total_cost = 0;
    $j("input.cost:checked").each(function() {
        total_cost += parseFloat($j(this).data('cost'));
    });
    $j("input.multicost").each(function() {
        total_cost += parseInt($j(this).val()) * parseFloat($j(this).data('cost'));
    });
    $j("input[name*='-option']:checked, input[name*='-siblingdiscount']:checked").each(function() {
        if ($j(this).data('is_custom')) {
            total_cost += parseFloat($j(this).parent().next().val()) || 0;
        } else {
            total_cost += parseFloat($j(this).data('cost'));
        }
    });
    total_cost += prog_cost;
    $j("#total_cost").html("$" + Number(total_cost).toFixed(2));
    amount_due = total_cost - amount_paid - amount_finaid;
    if (amount_due < 0) {
        $j("#amount_due").html("-$" + Number(-amount_due).toFixed(2)).css("color", "red");
        $j("#donation_warning").html("(Thank you for your donation!)").show();
    } else if (amount_due == 0) {
        $j("#amount_due").html("$" + Number(amount_due).toFixed(2)).css("color", "black");
        $j("#donation_warning").hide();
    } else {
        $j("#amount_due").html("$" + Number(amount_due).toFixed(2)).css("color", "black");
        $j("#donation_warning").html("(Don't forget to pay for your remaining balance!)").show();
    }
}

/*
 * A click handler that unchecks all inputs with the same name as the
 * button.
 **/
function remove_item(button) {
    $j("input[name="+button.name+"]").prop("checked", false);
    updateTotalCost();
}
