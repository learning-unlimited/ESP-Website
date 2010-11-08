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
