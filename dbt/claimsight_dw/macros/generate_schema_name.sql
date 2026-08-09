{#
  Use the custom schema name verbatim (staging / intermediate / marts) instead
  of dbt's default "<target>_<custom>" so the warehouse schemas are clean and
  predictable for the reporting layer and BI tools to reference.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}


{#
  Cross-format date parser mirroring the Python/SQL cs_parse_date used by the
  data-quality engine, so staging can parse the deliberately mixed date formats.
#}
{% macro parse_date(col) -%}
    (case
        when {{ col }} is null or {{ col }} = '' then null
        when {{ col }} ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}' then to_date(substr({{ col }}, 1, 10), 'YYYY-MM-DD')
        when {{ col }} ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' then to_date({{ col }}, 'DD/MM/YYYY')
        when {{ col }} ~ '^[0-9]{2}-[0-9]{2}-[0-9]{4}$' then to_date({{ col }}, 'DD-MM-YYYY')
        else null
    end)
{%- endmacro %}


{#
  Deterministic surrogate key from one or more columns (avoids a dbt_utils
  dependency). Nulls are coalesced so the hash is stable.
#}
{% macro surrogate_key(fields) -%}
    md5(
        {%- for f in fields %}
        coalesce(cast({{ f }} as varchar), '_null_'){{ " || '|' ||" if not loop.last }}
        {%- endfor %}
    )
{%- endmacro %}
