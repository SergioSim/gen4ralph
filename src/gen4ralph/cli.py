"""Gen4Ralph CLI entrypoint."""

import json
import logging
import re
import sys
from typing import TextIO

import click
import click_log
from genson import SchemaBuilder

logger = logging.getLogger(__name__)
click_log.basic_config(logger)


@click.command()
@click_log.simple_verbosity_option(logger)
def cli():
    """Gen4Ralph generates JSON Schemas and pydantic models for ralph."""

    logger.info("Generating JSON schemas using genson")

    for schema in generate_json_schemas(sys.stdin):
        click.echo(schema)


def generate_json_schemas(input_file: TextIO):
    """Generates JSON schemas reading from input file line by line."""

    json_schemas = {}
    for event_str in input_file:
        add_event_to_schemas(event_str, json_schemas)

    for schema in json_schemas.values():
        yield json.dumps(schema)


def add_event_to_schemas(event_str: str, json_schemas: dict):
    """Tries to add the event schema to the json_schemas dict."""

    try:
        event = json.loads(event_str)
    except (json.JSONDecodeError, TypeError):
        logger.error("Input event is not a valid JSON string")
        return
    if "event_source" not in event or "event_type" not in event:
        logger.error("Input event is missing `event_source` or `event_type`")
        return
    event = replace_pattern_properties_and_jsons(event)

    title = get_title(event)
    builder = SchemaBuilder()
    # Retrieve the schema by title, if we have already defined it before or use a new one.
    new_schema = {"title": title, "type": "object", "properties": {}}
    builder.add_schema(json_schemas.get(title, new_schema))
    # Update the schema with the current event.
    builder.add_object(event)
    # Store the updated schema in json_schemas.
    json_schemas[title] = builder.to_schema()


def get_title(event: dict):
    """Returns the title for the event."""

    context = event.get("context", {})
    if (
        event["event_source"] == "server"
        and isinstance(context, dict)
        and context.get("path", {}) == event["event_type"]
    ):
        return "ServerEventModel"
    # The title of browser event `seq_goto` should be `SeqGotoBrowserEventModel`.
    title = f"{event['event_type']}.{event['event_source']}.event.model"
    return "".join(x.capitalize() for x in title.replace("_", ".").split("."))


def replace_pattern_properties_and_jsons(event):
    """Replaces pattern properties matching regex with a single pattern.

    And replaces JSON strings with dictionaries (adding _JSON suffix to the keys).

    This reduces the JSON schema size, genson treats each pattern property as an optional property.
    Example:
        Replaces `cc2a00e69f7a4dd8b560f4e48911206f_3_1` with `MD5HASH_int_int_0`.
        Replaces `"key": "{\"foo\": {}}"` with `"key_JSON": { "foo": {}}`
    """

    count = 0
    result = {}
    for key, item in event.items():
        if re.match(r"^[a-f0-9]{32}_[0-9]+_[0-9]+$", key):
            key = f"MD5HASH_int_int_{count}"
            count += 1
        if isinstance(item, dict):
            result[key] = replace_pattern_properties_and_jsons(item)
            continue
        if isinstance(item, str):
            # Try to parse JSON:
            try:
                parsed_item = json.loads(item)
                if isinstance(parsed_item, dict):
                    result[key + "_JSON"] = replace_pattern_properties_and_jsons(
                        parsed_item
                    )
                    continue
            except (json.JSONDecodeError, TypeError):
                pass
        result[key] = item
    return result
