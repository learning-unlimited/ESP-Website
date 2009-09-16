{% spaceless %}
{% for timeslot in timeslots %}{% if not timeslot.1|length_is:0 %}{% if allow_removal %}
    {% for cls in timeslot.1 %}
    register_link({id: 'remove_{{ timeslot.0.id }}_{{ cls.section.id }}', url: '/learn/{{ prog.getUrlBase }}/ajax_clearslot/{{ timeslot.0.id }}?sec_id={{ cls.section.id }}'});
    {% endfor %}
{% endif %}{% endif %}{% endfor %}
{% endspaceless %}
