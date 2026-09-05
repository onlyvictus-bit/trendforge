from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from . import storage
from .harmonic_lifecycle import HarmonicLifecycleInput, evaluate_harmonic_lifecycle


T0 = datetime(2026, 7, 1, 9, 15, tzinfo=timezone.utc)


def _bar(day: int, *, high: float, low: float, close: float) -> dict[str, Any]:
    return {
        "timestamp": (T0 + timedelta(days=day)).isoformat(),
        "high": high,
        "low": low,
        "close": close,
    }


def _base(name: str) -> dict[str, Any]:
    return {
        "patternKey": f"TF_LIFE_{name}",
        "symbol": "TFLIFE",
        "timeframe": "1d",
        "patternName": "GARTLEY",
        "direction": "bullish",
        "asOf": (T0 + timedelta(days=3)).isoformat(),
        "completedAt": T0.isoformat(),
        "expiresAt": (T0 + timedelta(days=10)).isoformat(),
        "przLow": 99,
        "przHigh": 101,
        "triggerPrice": 102,
        "invalidationPrice": 95,
        "target1": 105,
        "target2": 110,
        "target3": 115,
        "bars": [_bar(0, high=101, low=99, close=100)],
    }


def build_lifecycle_fixture_inputs() -> dict[str, HarmonicLifecycleInput]:
    rows: dict[str, dict[str, Any]] = {}
    forming = _base("FORMING")
    forming["completedAt"] = None
    forming["bars"] = []
    rows["FORMING"] = forming

    complete = _base("COMPLETE")
    complete["asOf"] = T0.isoformat()
    rows["COMPLETE"] = complete

    triggered = _base("TRIGGERED")
    triggered["bars"].append(_bar(1, high=103, low=99, close=102.5))
    rows["TRIGGERED"] = triggered

    invalidated = _base("INVALIDATED")
    invalidated["bars"].append(_bar(1, high=101, low=94, close=95))
    rows["INVALIDATED"] = invalidated

    for name, target_high in (("WIN_T1", 106), ("WIN_T2", 111), ("WIN_T3", 116)):
        win = _base(name)
        win["bars"].extend(
            [
                _bar(1, high=103, low=99, close=102.5),
                _bar(2, high=target_high, low=101, close=target_high - 0.5),
            ]
        )
        rows[name] = win

    loss = _base("LOSS")
    loss["bars"].extend(
        [
            _bar(1, high=103, low=99, close=102.5),
            _bar(2, high=103, low=94, close=95),
        ]
    )
    rows["LOSS"] = loss

    expired = _base("EXPIRED")
    expired["asOf"] = (T0 + timedelta(days=11)).isoformat()
    expired["bars"].append(_bar(11, high=101, low=99, close=100))
    rows["EXPIRED"] = expired
    return {
        name: HarmonicLifecycleInput.model_validate(deepcopy(payload))
        for name, payload in rows.items()
    }


def load_lifecycle_fixture_events() -> dict[str, Any]:
    results = [
        evaluate_harmonic_lifecycle(item)
        for item in build_lifecycle_fixture_inputs().values()
    ]
    saved = sum(
        storage.save_harmonic_lifecycle_events(
            result.model_dump(mode="json", by_alias=True)
        )
        for result in results
    )
    return {
        "mode": "DETERMINISTIC_DEMO",
        "scenarioCount": len(results),
        "savedEvents": saved,
        "stateCounts": dict(
            sorted(Counter(result.state for result in results).items())
        ),
        "executable": False,
    }
