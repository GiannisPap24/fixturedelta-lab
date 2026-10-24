"""Small shared validation and bounded diagnostic helpers."""

import json

from fixturedelta_lab.domain import ContractError


def validate_inputs(output: str, expectation: object, expected_type: type) -> None:
    if not isinstance(output, str):
        raise ContractError("output: expected a string")
    if not isinstance(expectation, expected_type):
        raise ContractError(f"expectation: expected {expected_type.__name__}")


def preview(value: str) -> str:
    """Escape control/Unicode characters; bound text disclosure to 80 code points."""
    quoted = json.dumps(value[:80], ensure_ascii=True)
    return f"{quoted} (truncated; {len(value)} code points)" if len(value) > 80 else quoted
