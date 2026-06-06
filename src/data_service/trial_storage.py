import datetime as dt
import json

import psycopg2.extras


JSONB_STORAGE = "jsonb"
DEFAULT_STORAGE = "column"
DEFAULT_FRACTION_TABLE_FIELDS = {
    "fraction_number",
    "fraction_name",
    "fraction_date",
    "num_gating_events",
    "mvsdd",
    "kvsdd",
    "kv_pixel_size",
    "mv_pixel_size",
    "marker_length",
    "marker_width",
    "marker_type",
    "imaging_kv",
    "imaging_ms",
    "imaging_ma",
}


def get_section_structure(trial_structure, section):
    if not isinstance(trial_structure, dict):
        return {}
    section_structure = trial_structure.get(section, {})
    return section_structure if isinstance(section_structure, dict) else {}


def get_field_config(trial_structure, section, field_name):
    section_structure = get_section_structure(trial_structure, section)
    field_config = section_structure.get(field_name, {})
    if not field_config:
        lowered_field_name = field_name.lower()
        for candidate_name, candidate_config in section_structure.items():
            if candidate_name.lower() == lowered_field_name:
                field_config = candidate_config
                break
    return field_config if isinstance(field_config, dict) else {}


def get_field_storage(trial_structure, section, field_name):
    return get_field_config(trial_structure, section, field_name).get(
        "storage", DEFAULT_STORAGE
    )


def is_jsonb_field(trial_structure, section, field_name):
    return get_field_storage(trial_structure, section, field_name) == JSONB_STORAGE


def get_field_table(trial_structure, section, field_name, fraction_table_fields=None):
    if section == "prescription":
        return "prescription"

    if section != "fraction":
        return section

    field_config = get_field_config(trial_structure, section, field_name)
    explicit_table = (
        field_config.get("storage_table")
        or field_config.get("storage_target")
        or field_config.get("table")
    )
    if explicit_table in ("fraction", "images"):
        return explicit_table

    table_fields = fraction_table_fields or DEFAULT_FRACTION_TABLE_FIELDS
    normalized_table_fields = {field.lower() for field in table_fields}
    if field_name.lower() in normalized_table_fields:
        return "fraction"

    return "images"


def get_trial_fields(trial_structure, section, storage=None):
    section_structure = get_section_structure(trial_structure, section)
    fields = []
    for field_name, field_config in section_structure.items():
        if storage is None:
            fields.append(field_name)
            continue
        if not isinstance(field_config, dict):
            continue
        if field_config.get("storage", DEFAULT_STORAGE) == storage:
            fields.append(field_name)
    return fields


def parse_extended_data(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        if value.strip() == "":
            return {}
        try:
            parsed_value = json.loads(value)
            return parsed_value if isinstance(parsed_value, dict) else {}
        except ValueError:
            return {}
    return {}


def get_extended_data(row, section):
    return parse_extended_data(
        row.get(f"{section}_extended_data", row.get("extended_data"))
    )


def get_stored_field_value(
    row,
    trial_structure,
    section,
    field_name,
    fraction_table_fields=None,
):
    if is_jsonb_field(trial_structure, section, field_name):
        table_name = get_field_table(
            trial_structure,
            section,
            field_name,
            fraction_table_fields=fraction_table_fields,
        )
        return get_extended_data(row, table_name).get(field_name)
    return row.get(field_name.lower(), row.get(field_name))


def split_values_by_storage(values, trial_structure, section):
    column_values = {}
    jsonb_values = {}
    for field_name, value in values.items():
        if is_jsonb_field(trial_structure, section, field_name):
            jsonb_values[field_name] = value
        else:
            column_values[field_name] = value
    return column_values, jsonb_values


def split_values_by_storage_table(
    values,
    trial_structure,
    section,
    fraction_table_fields=None,
):
    column_values = {}
    jsonb_values_by_table = {}
    for field_name, value in values.items():
        if is_jsonb_field(trial_structure, section, field_name):
            table_name = get_field_table(
                trial_structure,
                section,
                field_name,
                fraction_table_fields=fraction_table_fields,
            )
            jsonb_values_by_table.setdefault(table_name, {})[field_name] = value
        else:
            column_values[field_name] = value
    return column_values, jsonb_values_by_table


def json_safe_value(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dt.timedelta):
        return str(value)
    return value


def jsonb_insert_value(value):
    return psycopg2.extras.Json(json_safe_value(value))


def set_jsonb_field(cur, table_name, id_column, id_value, field_name, value):
    if value is None:
        cur.execute(
            f"""
            UPDATE {table_name}
            SET extended_data = COALESCE(extended_data, '{{}}'::jsonb) - %s
            WHERE {id_column} = %s
            """,
            (field_name, id_value),
        )
        return

    cur.execute(
        f"""
        UPDATE {table_name}
        SET extended_data = jsonb_set(
            COALESCE(extended_data, '{{}}'::jsonb),
            %s::text[],
            %s::jsonb,
            true
        )
        WHERE {id_column} = %s
        """,
        ([field_name], jsonb_insert_value(value), id_value),
    )


def set_jsonb_fields(cur, table_name, id_column, id_value, values):
    for field_name, value in values.items():
        set_jsonb_field(cur, table_name, id_column, id_value, field_name, value)


def build_extended_data(values):
    return {
        field_name: json_safe_value(value)
        for field_name, value in values.items()
        if value is not None
    }


def jsonb_select_expression(table_name, field_name, alias=None):
    alias = alias or field_name
    escaped_field = field_name.replace("'", "''")
    escaped_alias = alias.replace('"', '""')
    return f"{table_name}.extended_data ->> '{escaped_field}' AS \"{escaped_alias}\""
