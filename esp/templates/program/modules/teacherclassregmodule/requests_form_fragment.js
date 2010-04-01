{% for form in formset.forms %}
register_link({id: "remove_request_{{ forloop.counter0 }}", url: "/teach/{{ program.getUrlBase }}/ajax_requests", content: {action: "remove", form: "{{ forloop.counter0 }}"}, post_form: "clsform"});{% endfor %}
