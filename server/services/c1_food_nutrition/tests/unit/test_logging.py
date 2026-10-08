import json
import logging

from c1_food_nutrition.core.context import request_id_var
from c1_food_nutrition.core.logging import JsonFormatter


def make_record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord("c1.test", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_includes_standard_and_extra_fields() -> None:
    token = request_id_var.set("req-1")
    try:
        line = JsonFormatter().format(make_record(item_count=2))
    finally:
        request_id_var.reset(token)

    payload = json.loads(line)
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "c1.test"
    assert payload["request_id"] == "req-1"
    assert payload["item_count"] == 2
    assert "args" not in payload


def test_json_formatter_without_request_context() -> None:
    assert json.loads(JsonFormatter().format(make_record()))["request_id"] is None
