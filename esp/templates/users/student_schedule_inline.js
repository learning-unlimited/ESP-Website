if (reg_open_status == null) {
  var reg_open_status = false;
}
var reg_open_new_status = {% if reg_open %}true{% else %}false{% endif %};
if (reg_open_new_status != reg_open_status) {
  reg_open_status = reg_open_new_status;
  if (reg_open_status) {
    $j(".addbutton").css({visibility: "visible"})
  } else {
    $j(".addbutton").css({visibility: "hidden"})
  }
}
{% for timeslot in timeslots %}{% if not timeslot.1|length_is:0 %}{% if allow_removal %}
    {% for cls in timeslot.1 %}
    register_link({id: "remove_{{ timeslot.0.id }}_{{ cls.section.id }}", url: "/learn/{{ prog.getUrlBase }}/ajax_clearslot/{{ timeslot.0.id }}?sec_id={{ cls.section.id }}"});
    {% endfor %}
{% endif %}{% endif %}{% endfor %}

{% if not request.user.onsite_local %}
$j(function() {
    // Create two dialog boxes with two different warning messages,
    // one that appears when you try to remove an enrolled class,
    // and another that appears when you try removing a non-enrolled class.
    // autoOpen: false makes it so that the dialog boxes don't appear on page load.
    $j( "div.remove-confirm" ).dialog({
        resizable: false,
        modal: true,
        autoOpen: false,
        closeOnEscape: false,
    });

    // When clicking any remove link, handle the event here rather than immediately removing the class.
    // Display a warning dialog box, and give the user an option to confirm the removal or cancel it.
    $j("a.remove").click( function(eventObject) {

        // The hyperlink click is always cancelled at first.
        // If the user confirms the removal,
        // the clearslot link is followed, and the class is removed.
        eventObject.preventDefault();
        var $a_remove_tag = $j(this);
        var cls_code = $j(this).attr("data-sec-code");
        var remove_type = $j(this).attr("data-remove-type");    // "enrolled" for enrolled classes, "applied" for non-enrolled classes
        $j( "#"+remove_type+"-remove-confirm" ).dialog( "option", "title", "Remove class "+cls_code+"?" ).dialog( "option", "buttons", {
                "Remove class": function() {
                    $j( this ).dialog( "close" );
                    window.location.replace($a_remove_tag.attr("href"));
                },
                Cancel: function() {
                    $j( this ).dialog( "close" );
                }
        }).dialog( "open" );
    });
});
{% endif %}

