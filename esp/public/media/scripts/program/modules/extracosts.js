var amount_paid = 0;
var finaid_percent = 0;
var finaid_max_dec = 0;
var amount_finaid = 0;
var amount_due = 0;
var prog_cost = 0;

$j(function() { 
    amount_paid = parseFloat($j("#amount_paid").data("total"));
    finaid_percent = (parseFloat($j("#amount_finaid").data("percent")) || 0) * 0.01;
    finaid_max_dec = parseFloat($j("#amount_finaid").data("max_dec")) || 0;
    prog_cost = parseFloat($j("#amount_cost").data("total")) || 0;
    updateTotalCost();
    $j("input[name*='-cost']").on('change', updateTotalCost);
    $j("input[name*='-count']").on('change', updateTotalCost);
    $j("input[name*='-option']").on('change', updateTotalCost);
    $j("input[name*='-siblingdiscount']").on('change', updateTotalCost);
});

function updateTotalCost() {
    var cost = 0;
    var total_cost = 0;
    var finaid_covered = 0;
    $j("input.cost:checked").each(function() {
        cost = parseFloat($j(this).data('cost'));
        total_cost += cost;
        if ($j(this).data('for_finaid')) finaid_covered += cost;
    });
    $j("input.multicost").each(function() {
        cost = parseInt($j(this).val()) * parseFloat($j(this).data('cost'))
        total_cost += cost;
        if ($j(this).data('for_finaid')) finaid_covered += cost;
    });
    $j("input[name*='-option']:checked, input[name*='-siblingdiscount']:checked").each(function() {
        if ($j(this).data('is_custom')) {
            cost = parseFloat($j(this).parent().next().val()) || 0;
            total_cost += cost;
            if ($j(this).data('for_finaid')) finaid_covered += cost;
        } else {
            cost = parseFloat($j(this).data('cost'));
            total_cost += cost;
            if ($j(this).data('for_finaid')) finaid_covered += cost;
        }
    });
    total_cost += prog_cost;
    finaid_covered += prog_cost;
    $j("#total_cost").html("$" + Number(total_cost).toFixed(2));
    amount_finaid = Math.min(finaid_covered, finaid_max_dec);
    if (amount_finaid < finaid_covered) amount_finaid += (finaid_covered - amount_finaid) * finaid_percent;
    $j("#amount_finaid").html("-$" + Number(amount_finaid).toFixed(2));
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
