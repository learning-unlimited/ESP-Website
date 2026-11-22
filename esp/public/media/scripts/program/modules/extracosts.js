var amount_paid = 0;
var finaid_percent = 0;
var finaid_max_dec = 0;
var amount_finaid = 0;
var amount_due = 0;
var prog_cost = 0;

$j(function () {
  // the amount that has already been paid
  amount_paid = parseFloat($j("#amount_paid").data("total")) || 0;
  // the amount of donations that were promised
  amount_donation = parseFloat($j("#amount_donation").data("donation")) || 0;
  // the dollar amount of financial aid that is provided
  finaid_max_dec = parseFloat($j("#amount_finaid").data("max_dec")) || 0;
  // the percent of remaining cost that is covered by financial aid
  finaid_percent =
    (parseFloat($j("#amount_finaid").data("percent")) || 0) * 0.01;
  // the cost of the program; this is zero if there is a sibling discount field in the form
  prog_cost = parseFloat($j("#amount_cost").data("total")) || 0;
  // update the costs on the page
  updateTotalCost();
  // anytime anything in the form is changed, update the costs
  $j("input[name*='-cost']").on("change", updateTotalCost);
  $j("input[name*='-count']").on("change", updateTotalCost);
  $j("input[name*='-option']").on("change", function () {
    updateCustomAmountEnabled();
    updateTotalCost();
  });
  $j("input.option-custom-amount").on("input change", updateTotalCost);
  $j("input[name*='-siblingdiscount']").on("change", updateTotalCost);
  // a custom amount is only editable while its option is selected
  updateCustomAmountEnabled();
});

/*
 * Enable the custom-amount input of each multi-select option only while that
 * option's checkbox is checked, so that students can't type an amount for
 * something they haven't selected. Disabled inputs are not submitted, which
 * also keeps stale amounts out of the POST data.
 **/
function updateCustomAmountEnabled() {
  $j("input.option-custom-amount").each(function () {
    var checkbox = $j(
      "input[name*='-options'][value='" + $j(this).data("option-id") + "']",
    );
    // leave single-select custom amounts (which have no checkbox) alone
    if (checkbox.length) $j(this).prop("disabled", !checkbox.prop("checked"));
  });
}

/*
 * Return the custom amount entered for the given option ID, or null if that
 * option is not rendered with a dedicated custom-amount input.
 **/
function getCustomAmount(option_id) {
  var input = $j(
    "input.option-custom-amount[data-option-id='" + option_id + "']",
  );
  if (!input.length) return null;
  return parseFloat(input.val()) || 0;
}

function updateTotalCost() {
  var cost = 0;
  var total_extras = 0;
  // only items marked as such are covered by financial aid
  var finaid_covered = 0;
  $j("input.cost:checked").each(function () {
    cost = parseFloat($j(this).data("cost"));
    total_extras += cost;
    if ($j(this).data("for_finaid")) finaid_covered += cost;
  });
  $j("input.multicost").each(function () {
    cost = (parseInt($j(this).val()) || 0) * parseFloat($j(this).data("cost"));
    total_extras += cost;
    if ($j(this).data("for_finaid")) finaid_covered += cost;
  });
  $j(
    "input[name*='-option']:checked, input[name*='-siblingdiscount']:checked",
  ).each(function () {
    if ($j(this).data("is_custom")) {
      cost = getCustomAmount($j(this).val());
      // fall back to the single-select layout, where the custom amount input
      // is the sibling of the radio button's label
      if (cost === null) cost = parseFloat($j(this).parent().next().val()) || 0;
      total_extras += cost;
      if ($j(this).data("for_finaid")) finaid_covered += cost;
    } else {
      cost = parseFloat($j(this).data("cost"));
      total_extras += cost;
      if ($j(this).data("for_finaid")) finaid_covered += cost;
    }
  });
  // update the extras total on the page
  $j("#total_extras").html("$" + Number(total_extras).toFixed(2));
  // program admission is always covered by financial aid
  finaid_covered += prog_cost;
  // calculate how much is covered by financial aid
  amount_finaid = Math.min(finaid_covered, finaid_max_dec);
  if (amount_finaid < finaid_covered)
    amount_finaid += (finaid_covered - amount_finaid) * finaid_percent;
  // update the financial aid total on the page (should always be negative)
  if (amount_finaid > 0)
    $j("#amount_finaid").html("-$" + Number(amount_finaid).toFixed(2));
  // calculate the amount due after accounting for what has already been paid and what financial aid covers
  amount_due =
    total_extras + prog_cost + amount_donation - amount_paid - amount_finaid;
  // update the amount due on the page
  if (amount_due < 0) {
    $j("#amount_due")
      .html("-$" + Number(-amount_due).toFixed(2))
      .css("color", "red");
    $j("#donation_warning").html("(Thank you for your donation!)").show();
  } else if (amount_due == 0) {
    $j("#amount_due")
      .html("$" + Number(amount_due).toFixed(2))
      .css("color", "black");
    $j("#donation_warning").hide();
  } else {
    $j("#amount_due")
      .html("$" + Number(amount_due).toFixed(2))
      .css("color", "black");
    $j("#donation_warning")
      .html("(Don't forget to pay for your remaining balance!)")
      .show();
  }
}

/*
 * A click handler that unchecks all inputs with the same name as the
 * button.
 **/
function remove_item(button) {
  $j("input[name=" + button.name + "]").prop("checked", false);
  updateTotalCost();
}
