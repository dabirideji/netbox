"""Load and validate JSON payloads against bundled JSON Schema documents."""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

SCHEMA_NAMES = {
    "ui-preferences.patch": "ui-preferences.patch.schema.json",
    "platform-settings.patch": "platform-settings.patch.schema.json",
    "storage-settings.patch": "storage-settings.patch.schema.json",
}


def schemas_root() -> Path:
    """Return the directory containing bundled JSON Schema files."""

    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)) / "schemas"
    return Path(__file__).resolve().parents[2] / "schemas"


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> Draft202012Validator:
    filename = SCHEMA_NAMES.get(schema_name)
    if filename is None:
        raise KeyError(f"unknown schema: {schema_name}")

    path = schemas_root() / filename
    schema = json.loads(path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validation_error_message(error: ValidationError, schema_name: str) -> str:
    """Return a concise API-friendly validation error message."""

    path = ".".join(str(part) for part in error.absolute_path)
    if error.validator == "additionalProperties":
        match = re.search(r"\('([^']+)' was unexpected\)", error.message)
        extra = match.group(1) if match else str(error.message)
        if schema_name.startswith("ui-preferences"):
            return f"unknown preference key: {extra}"
        if schema_name.startswith("storage-settings"):
            return f"unknown storage settings field: {extra}"
        return f"unknown platform settings field: {extra}"
    if error.validator == "minProperties":
        if schema_name.startswith("ui-preferences"):
            return "at least one preference field is required"
        if schema_name.startswith("storage-settings"):
            return "at least one storage settings field is required"
        return "at least one platform settings field is required"
    if path:
        return f"invalid value for {path}"
    return "payload failed schema validation"


def validate_json_schema(schema_name: str, payload: Any) -> None:
    """Validate one payload against a named schema, raising ValueError on failure."""

    validator = _validator(schema_name)
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    if not errors:
        return
    raise ValueError(validation_error_message(errors[0], schema_name))
