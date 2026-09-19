"""M1B static cutover verifier (read-only).

Proves the governed reader migration structurally, without executing the
system:

- no governed production reader resolves evidence through a physical locator;
- every governed reader goes through the exact-H1 resolver;
- the resolver module itself has no destructive surface;
- the legacy compatibility API still exists for provenance/diagnostics.

Exit 0 prints M1B_STATIC_GATE_PASS. Any violation prints FAIL lines.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API = REPO_ROOT / "backend" / "trendforge_api"

# file -> forbidden substrings (a hit fails the gate)
FORBIDDEN: dict[str, tuple[str, ...]] = {
    "r16_retention.py": (
        "SELECT object_path, size_bytes FROM market_data_objects",
        "path.open(",
        "file_digest",
    ),
    "market_data_alignment.py": (
        'entry.get("objectPath")',
        "object_path.read_bytes()",
    ),
    "derived_market_outputs.py": (
        "latest.object_path",
        "Path(latest.object_path)",
    ),
    "fii_stock_signals.py": (
        "object_path_value",
        "object_path.relative_to",
        "_objects_root",
        'getattr(attempt, "object_path"',
    ),
    "market_data_parameters.py": (
        "attempt.object_path",
        "Path(attempt.object_path)",
    ),
    "openalgo_replay.py": (
        "object_path_for_hash(",
        "path.read_bytes()",
    ),
    "selection/cash_a1_staging.py": (
        "object_path_for_hash(",
        "Path(latest.object_path)",
        "Path(path).read_bytes()",
    ),
    "selection/cash_a2_identity.py": (
        "object_path_for_hash(",
        "Path(latest.object_path)",
        "Path(path).read_bytes()",
    ),
    "selection/cash_post_commit.py": (
        "store.object_path_for_hash(",
        "Path(latest.object_path)",
        "path.read_bytes()",
        "if not path.is_file():",
    ),
    "selection/tradability.py": (
        "object_path_for_hash(",
    ),
}

# file -> required substrings (a miss fails the gate)
REQUIRED: dict[str, tuple[str, ...]] = {
    "r16_retention.py": ("tiering_for_connection", "read_object_exact"),
    "market_data_alignment.py": ("self._tiering.read_object_exact",),
    "derived_market_outputs.py": ("self.store.read_object_exact",),
    "fii_stock_signals.py": ("self._store.read_object_exact",),
    "market_data_parameters.py": ("self.store.read_object_exact",),
    "openalgo_replay.py": ("self.store.read_object_exact",),
    "selection/cash_a1_staging.py": (
        "market.read_object_exact",
        "raw_path=latest.object_path",
    ),
    "selection/cash_a2_identity.py": ("market.read_object_exact",),
    "selection/cash_post_commit.py": (
        "store.read_object_exact",
        "exact_object_available",
    ),
    "selection/tradability.py": ("market_store.read_object_exact",),
    "market_data_store.py": (
        "def object_path_for_hash",
        "def read_object_exact",
        "def exact_object_available",
    ),
}

# The resolver must have no destructive surface of its own.
RESOLVER_FORBIDDEN = (
    "shutil",
    "os.replace",
    "os.rename",
    ".unlink(",
    "os.remove",
    "rmtree",
    ".move(",
    "def move_",
    "def delete_",
)


def _read(relative: str) -> str:
    path = API / relative
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _code_only(text: str) -> str:
    """Strip docstrings and comments so prose cannot trip the gate."""
    out: list[str] = []
    in_docstring = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('"""'):
            if stripped.count('"""') == 2 and len(stripped) > 3:
                continue
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        code = line.split("#", 1)[0]
        out.append(code)
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    del argv
    failures: list[str] = []
    for relative, tokens in FORBIDDEN.items():
        text = _code_only(_read(relative))
        if not text:
            failures.append(f"FAIL missing governed file: {relative}")
            continue
        for token in tokens:
            if token in text:
                failures.append(
                    f"FAIL legacy path construct in {relative}: {token!r}"
                )
    for relative, tokens in REQUIRED.items():
        text = _read(relative)
        for token in tokens:
            if token not in text:
                failures.append(
                    f"FAIL missing exact-H1 construct in {relative}: {token!r}"
                )
    resolver = _code_only(_read("retention_tiering.py"))
    if not resolver:
        failures.append("FAIL missing module: retention_tiering.py")
    else:
        for token in RESOLVER_FORBIDDEN:
            if token in resolver:
                failures.append(
                    f"FAIL destructive surface in retention_tiering.py: {token!r}"
                )
        if "def read_object_exact" not in resolver:
            failures.append("FAIL resolver lacks read_object_exact")
    if failures:
        for line in failures:
            print(line)
        return 1
    print("M1B_STATIC_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
