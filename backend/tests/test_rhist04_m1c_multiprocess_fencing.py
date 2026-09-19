"""R-HIST-04 GATE 0 — multiprocess M1C fencing (BLOCKING for M2A).

Eight independent OS processes (not threads) contend for one movement claim
on one scratch SQLite journal. Exactly one process may win; losers must lose
cleanly; a stale token must never transition after authority moves.

Deterministic cleanup, bounded timeouts, no sleeps for correctness.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from trendforge_api.market_data_store import MarketDataStore
from trendforge_api.retention_moves import MoveJournalStore
from trendforge_api.retention_tiering import RetentionTieringStore

WORKER_SCRIPT = r"""
import sys
from trendforge_api.retention_moves import MoveJournalStore, MoveAuthorityLostError

db_path, move_id, version = sys.argv[1], sys.argv[2], int(sys.argv[3])
journal = MoveJournalStore(db_path=__import__("pathlib").Path(db_path))
try:
    claim = journal.claim_move(
        move_id, expected_state="PENDING_COPY", expected_version=version
    )
except MoveAuthorityLostError as exc:
    print(f"RESULT LOST {exc}")
else:
    print(f"RESULT WON epoch={claim.worker_epoch} version={claim.state_version}")
"""


def _one_move(tmp_path: Path):
    store = MarketDataStore(
        root=tmp_path / "market-data", db_path=tmp_path / "market.db"
    )
    ref = store.install_object(
        b'{"h1": "mp-fence"}', extension="json", media_type="application/json"
    )
    tiering = RetentionTieringStore(
        objects_root=tmp_path / "market-data" / "objects",
        db_path=tmp_path / "market.db",
    )
    replica_id = tiering.adopt_legacy_as_replica(
        ref.content_hash,
        tier="HOT",
        backend_id="local-hot",
        failure_domain="test-fd-1",
    )
    journal = MoveJournalStore(db_path=tmp_path / "market.db")
    mirror = tmp_path / "warm-mirror"
    created = journal.create_move_intent(
        content_hash=ref.content_hash,
        source_replica_id=replica_id,
        destination_tier="WARM",
        destination_backend_id="local-warm",
        destination_object_key=f"warm/{ref.content_hash[:2]}.json",
        destination_locator=str(mirror / f"{ref.content_hash}.json"),
        representation="RAW",
        representation_version="v1",
        operation_kind="COPY",
    )
    return journal, created


def test_eight_processes_exactly_one_claim_winner(tmp_path: Path) -> None:
    journal, created = _one_move(tmp_path)
    backend = Path(__file__).resolve().parents[1]
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", WORKER_SCRIPT,
             str(tmp_path / "market.db"), created.move_id,
             str(created.state_version)],
            cwd=str(backend),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(8)
    ]
    try:
        outputs = []
        for process in processes:
            try:
                stdout, _ = process.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                process.kill()
                raise
            outputs.append(stdout)
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
    winners = [line for line in outputs if "RESULT WON" in line]
    losers = [line for line in outputs if "RESULT LOST" in line]
    assert len(winners) == 1, outputs
    assert len(losers) == 7, outputs

    stored = journal.get_move(created.move_id)
    assert stored is not None
    assert stored.worker_epoch == 1
    assert stored.state_version == created.state_version + 1
    assert stored.state == "PENDING_COPY"
    # Journal remains readable and consistent.
    assert journal.get_move(created.move_id).move_id == created.move_id


def test_stale_token_cannot_transition_after_authority_moves(
    tmp_path: Path,
) -> None:
    from trendforge_api.retention_moves import MoveAuthorityLostError

    journal, created = _one_move(tmp_path)
    backend = Path(__file__).resolve().parents[1]
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", WORKER_SCRIPT,
             str(tmp_path / "market.db"), created.move_id,
             str(created.state_version)],
            cwd=str(backend),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(4)
    ]
    try:
        outputs = []
        for process in workers:
            try:
                stdout, _ = process.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                process.kill()
                raise
            outputs.append(stdout)
    finally:
        for process in workers:
            if process.poll() is None:
                process.kill()
    assert sum("RESULT WON" in line for line in outputs) == 1

    winner = journal.get_move(created.move_id)
    assert winner is not None
    # A fresh claim moves authority forward; the winner token is now stale.
    journal.claim_move(
        created.move_id,
        expected_state="PENDING_COPY",
        expected_version=winner.state_version,
    )
    with pytest.raises(MoveAuthorityLostError):
        journal.transition_move(
            created.move_id,
            expected_state="PENDING_COPY",
            expected_version=winner.state_version,
            worker_epoch=winner.worker_epoch,
            new_state="COPY_IN_PROGRESS",
        )
    # Losers holding only the creation snapshot cannot transition either.
    with pytest.raises(MoveAuthorityLostError):
        journal.transition_move(
            created.move_id,
            expected_state="PENDING_COPY",
            expected_version=created.state_version,
            worker_epoch=created.worker_epoch,
            new_state="COPY_IN_PROGRESS",
        )
    stored = journal.get_move(created.move_id)
    assert stored is not None
    assert stored.state == "PENDING_COPY"
