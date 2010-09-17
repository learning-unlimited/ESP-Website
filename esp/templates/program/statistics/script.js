
register_form({id: "statistics_form", url: "/manage/statistics/"});


{% for field_name in field_ids %}
clear_widget("{{ field_name }}");{% endfor %}

dojo.parser.parse();

{% for field_name in field_ids %}
setup_update("{{ field_name }}");{% endfor %}
