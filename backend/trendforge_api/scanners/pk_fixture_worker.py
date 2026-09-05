"""One-shot JSON fixture worker for the development-only PK harness."""

from __future__ import annotations

import json
import os
import sys
import time

from .pk_compatibility import PKSanitizedFixture, PKShadowOutput


MAX_STDIN_BYTES = 1_000_000


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
    if len(raw) > MAX_STDIN_BYTES:
        return 20
    try:
        envelope = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 21

    fault_mode = str(envelope.get("faultMode", "NONE"))
    if fault_mode == "CRASH":
        return 22
    if fault_mode == "TIMEOUT":
        time.sleep(5)
    if fault_mode == "INVALID_JSON":
        sys.stdout.write("not-json")
        return 0
    if fault_mode == "OVERSIZED_OUTPUT":
        sys.stdout.write("x" * 100_000)
        return 0
    if fault_mode == "EXECUTABLE_ARTIFACT":
        os._exit(23)

    try:
        fixture = PKSanitizedFixture.model_validate(envelope["fixture"])
    except (KeyError, ValueError):
        return 24

    matched = tuple(
        sorted(row.symbol for row in fixture.rows if row.close > fixture.threshold)
    )
    output = PKShadowOutput(matched_symbols=matched)
    sys.stdout.write(output.model_dump_json(by_alias=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
