<?php
/*
    Auto generated {{ now() | datetimeformat }} from {{source}}
*/

class {{ filename }} extends Migration
{
    public function up()
    {
{%- for table in tables %}

        $this->createTableIfNotExists('{{ table.name }}', array(
        {%- for column in table.columns %}
            '{{column.name}}' => '{{column.type}}{% if column.extra != "" %} {{column.extra|quote}}{% endif %}'{% if not loop.last or table.constraints|count>0 %},{% endif -%}
        {% endfor %}
        {%- for constraint in table.constraints %}
            '{% if constraint.name %}constraint {{constraint.name}} {% endif %}{{constraint.type|default('')}} {{ constraint.storage|default('') }}' => '({{constraint.columns|join(', ')}})'{% if not loop.last %},{% endif %}
        {% endfor %}
        ));
        {%- for index in table.indexes %}

        $this->createIndexIfNotExists('{{ table.name }}', '{{ index.name }}',
            '{{ index.columns | join(', ') }}'{% if index.type %}, '{{ index.type }}'{% endif %}
        );{% endfor -%}
{% endfor %}
    }
}
