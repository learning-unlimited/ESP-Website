
register_form({id: "statistics_form", url: "/manage/statistics/"});

{% for field_name in field_ids %}
setup_update("{{ field_name }}");
{% endfor %}
