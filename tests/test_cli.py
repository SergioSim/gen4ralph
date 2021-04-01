"""Tests for gen4ralph cli."""

import json

import pytest
from click.testing import CliRunner

from gen4ralph.cli import cli


@pytest.mark.parametrize("value", ["", "1", "foo", "{}", "[]", "None"])
def test_cli_cli_with_an_invalid_value(value):
    """Tests given an invalid value that cli don't writes to std output."""

    runner = CliRunner()
    result = runner.invoke(cli, ["-v", "CRITICAL"], input=value)
    assert result.output == ""


@pytest.mark.parametrize(
    "value",
    [
        # Missing `event_type` and `event_source`
        "",
        1,
        "foo",
        {},
        [],
        None,
        {"foo": None},
        # Missing `event_source`
        {"evnet_type": "foo"},
        # Missing `event_source`
        {"event_source": "foo"},
    ],
)
def test_cli_cli_with_an_invalid_edx_event(value):
    """Tests given an invalid edX event that cli don't writes to std output."""

    value = json.dumps(value)
    runner = CliRunner()
    result = runner.invoke(cli, ["-v", "CRITICAL"], input=value)
    assert result.output == ""


@pytest.mark.parametrize(
    "value,expected",
    [
        (
            {"event_source": "foo", "event_type": "bar"},
            {
                "$schema": "http://json-schema.org/schema#",
                "properties": {
                    "event_source": {"type": "string"},
                    "event_type": {"type": "string"},
                },
                "required": ["event_source", "event_type"],
                "title": "BarFooEventModel",
                "type": "object",
            },
        ),
        (
            {"event_source": "server", "event_type": "bar", "context": "invalid"},
            {
                "$schema": "http://json-schema.org/schema#",
                "properties": {
                    "event_source": {"type": "string"},
                    "event_type": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["context", "event_source", "event_type"],
                "title": "BarServerEventModel",
                "type": "object",
            },
        ),
        (
            {"event_source": "server", "event_type": "bar", "context": {}},
            {
                "$schema": "http://json-schema.org/schema#",
                "properties": {
                    "event_source": {"type": "string"},
                    "event_type": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["context", "event_source", "event_type"],
                "title": "BarServerEventModel",
                "type": "object",
            },
        ),
        (
            {
                "event_source": "server",
                "event_type": "bar",
                "context": {"path": "not_bar"},
            },
            {
                "$schema": "http://json-schema.org/schema#",
                "properties": {
                    "event_source": {"type": "string"},
                    "event_type": {"type": "string"},
                    "context": {
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                        "type": "object",
                    },
                },
                "required": ["context", "event_source", "event_type"],
                "title": "BarServerEventModel",
                "type": "object",
            },
        ),
        (
            # EdX Server event (source=="server", event_type==context__path)
            {"event_source": "server", "event_type": "bar", "context": {"path": "bar"}},
            {
                "$schema": "http://json-schema.org/schema#",
                "properties": {
                    "event_source": {"type": "string"},
                    "event_type": {"type": "string"},
                    "context": {
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                        "type": "object",
                    },
                },
                "required": ["context", "event_source", "event_type"],
                "title": "ServerEventModel",
                "type": "object",
            },
        ),
    ],
)
def test_cli_cli_with_a_valid_edx_event(value, expected):
    """Tests given a valid edX event that cli writes the schema to std output."""

    value = json.dumps(value)
    runner = CliRunner()
    result = runner.invoke(cli, ["-v", "CRITICAL"], input=value)
    assert json.loads(result.output) == expected


def test_cli_cli_with_multiple_valid_edx_events_merges_their_schema():
    """Tests given multiple valid edX events that cli merges their schema."""

    # Event group 1 (server events)
    event_1_1 = {
        "event_source": "server",
        "event_type": "bar",
        "context": {"path": "bar"},
        "098f6bcd4621d373cade4e832627b4f6_1_1": "test_md5_hash_detection",
    }
    event_1_2 = {
        "event_source": "server",
        "event_type": "bar1",
        "context": {"path": "bar1", "user_id": 1},
        "0e4e3b2681e8931c067a23c583c878d5_1_2": "test_md5_hash_detection",
        "6185ad8f9b97d91721ab0438b4a2048b_1_3": "test_md5_hash_detection_2",
    }
    event_1_3 = {
        "event_source": "server",
        "event_type": "bar2",
        "context": {"path": "bar2", "course_id": "foo"},
        "3273f5713f114c9145bafecef9e81b4b_21_66": "test_md5_hash_detection",
    }

    # Event group 2 (page_close broser events)

    event_2_1 = {
        "event_source": "browser",
        "event_type": "page_close",
        "ip": "a string",
    }
    event_2_2 = {
        "event_source": "browser",
        "event_type": "page_close",
        "event": json.dumps({"bar": "baz"}),
    }
    event_2_3 = {
        "event_source": "browser",
        "event_type": "page_close",
        "event": {"foo": "bar"},
    }

    events = "\n".join(
        json.dumps(x)
        for x in [event_1_1, event_2_1, event_1_2, event_2_2, event_1_3, event_2_3]
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["-v", "CRITICAL"], input=events)

    output_lines = result.output.splitlines()
    assert len(output_lines) == 2

    server_event_schema = json.loads(output_lines[0])
    browser_event_schema = json.loads(output_lines[1])

    assert server_event_schema == {
        "$schema": "http://json-schema.org/schema#",
        "properties": {
            "MD5HASH_int_int_0": {"type": "string"},
            "MD5HASH_int_int_1": {"type": "string"},
            "context": {
                "properties": {
                    "course_id": {"type": "string"},
                    "path": {"type": "string"},
                    "user_id": {"type": "integer"},
                },
                "required": ["path"],
                "type": "object",
            },
            "event_source": {"type": "string"},
            "event_type": {"type": "string"},
        },
        "required": ["MD5HASH_int_int_0", "context", "event_source", "event_type"],
        "title": "ServerEventModel",
        "type": "object",
    }

    assert browser_event_schema == {
        "$schema": "http://json-schema.org/schema#",
        "properties": {
            "event": {
                "properties": {"foo": {"type": "string"}},
                "required": ["foo"],
                "type": "object",
            },
            "event_JSON": {
                "properties": {"bar": {"type": "string"}},
                "required": ["bar"],
                "type": "object",
            },
            "event_source": {"type": "string"},
            "event_type": {"type": "string"},
            "ip": {"type": "string"},
        },
        "required": ["event_source", "event_type"],
        "title": "PageCloseBrowserEventModel",
        "type": "object",
    }
