
register_form({id: "statistics_form", url: "/manage/statistics/"});

{% if clear_first %}
{% for field_name in field_ids %}
clear_widget("{{ field_name }}");{% endfor %}
{% endif %}

dojo.parser.parse();

{% for field_name in field_ids %}
setup_update("{{ field_name }}");{% endfor %}
