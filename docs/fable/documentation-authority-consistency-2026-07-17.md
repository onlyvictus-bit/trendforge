# Documentation Authority Consistency - 2026-07-17

## Intent

Remove active references to the retired root path `TREND_FORGE_IMPLEMENTATION_PLAN.md` while preserving the complete historical plan and its consolidation evidence.

## Approved Scope

The user approved updates to `present.md`, `docs/DECISIONS.md`, and `frontend/README.txt`, with the archived original and consolidation manifest retained unchanged.

## Decision

- The four active root Markdown documents are `AGENTS.md`, `present.md`, `TREND_FORGE_ARCHITECTURE.md`, and `TREND_FORGE_SOURCE_REGISTRY.md`.
- Current implementation order is authoritative in `present.md`, section `16. Build Order`.
- The former standalone implementation plan is historical evidence embedded under `EMBEDDED SOURCE: TREND_FORGE_IMPLEMENTATION_PLAN.md` in `present.md`.
- The unchanged archived source and `documentation_consolidation_manifest.json` remain the checksum-verifiable preservation record.
- Old filenames inside checksum-protected embedded or archived payloads remain unchanged because they are provenance text, not active-path guidance.

## Acceptance Criteria

- No active guidance points readers to the retired root plan path.
- `present.md` links to both the current Build Order and the embedded historical plan.
- The embedded plan remains an exact 4,446-line copy of the archived source.
- The archived plan, archived README, and consolidation manifest retain their pre-change SHA-256 hashes.

## Verification Evidence

- The active root plan path does not exist and no active document presents it as authoritative.
- The `current-build-order` and `embedded-source-implementation-plan` anchors each occur exactly once.
- The current embedded payload is line-for-line identical to all 4,446 archived source lines.
- Archived plan SHA-256 remained `492855467DD054282F14F513EF7C0D26C156C224AEF28C59C7D3975286AC1918`.
- Archived README SHA-256 remained `ED58DFF72D2C1663BF50BCF365F304E3365E654ACC3026A073D19C013DD92874`.
- Consolidation manifest SHA-256 remained `7FD2172724FA5D20CECCD7871F00A3D486D7CD4B2123F1E0E0F4572F07728532`.
- The archived plan hash matches the manifest source, embedded, and archive hash records.
