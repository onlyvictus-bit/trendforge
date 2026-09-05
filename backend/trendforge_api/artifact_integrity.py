from __future__ import annotations

import hashlib
import hmac
import io
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Literal
from urllib.parse import urlsplit


IntegrityState = Literal[
    "PASS", "WAIT_EMPTY_PARSE", "WAIT_PARSE_ERROR", "WAIT_SCHEMA_MISMATCH"
]


@dataclass(frozen=True)
class ArtifactIntegrityResult:
    state: IntegrityState
    reason: str
    content_hash: str
    content_length: int
    media_type: str
    response_length_matches: bool | None
    expected_hash_matches: bool | None
    members: tuple[dict[str, object], ...] = ()

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["contentHash"] = payload.pop("content_hash")
        payload["contentLength"] = payload.pop("content_length")
        payload["mediaType"] = payload.pop("media_type")
        payload["responseLengthMatches"] = payload.pop("response_length_matches")
        payload["expectedHashMatches"] = payload.pop("expected_hash_matches")
        payload["members"] = list(self.members)
        return payload


def _result(
    state: IntegrityState,
    reason: str,
    *,
    content_hash: str,
    content_length: int,
    media_type: str,
    response_length_matches: bool | None,
    expected_hash_matches: bool | None,
    members: tuple[dict[str, object], ...] = (),
) -> ArtifactIntegrityResult:
    return ArtifactIntegrityResult(
        state=state,
        reason=reason,
        content_hash=content_hash,
        content_length=content_length,
        media_type=media_type,
        response_length_matches=response_length_matches,
        expected_hash_matches=expected_hash_matches,
        members=members,
    )


def _unsafe_member_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    return bool(
        path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", normalized)
    )


def _zip_members(
    content: bytes,
    *,
    max_archive_members: int,
    max_uncompressed_bytes: int,
    max_compression_ratio: float,
) -> tuple[tuple[dict[str, object], ...] | None, str | None]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = [item for item in archive.infolist() if not item.is_dir()]
            if not infos:
                return None, "ZIP archive contains no files."
            if len(infos) > max_archive_members:
                return None, "ZIP archive exceeds the member-count safety limit."
            total_uncompressed = sum(item.file_size for item in infos)
            if total_uncompressed > max_uncompressed_bytes:
                return None, "ZIP archive exceeds the uncompressed-size safety limit."
            for item in infos:
                if _unsafe_member_name(item.filename):
                    return None, f"ZIP archive contains an unsafe path: {item.filename}"
                if item.flag_bits & 0x1:
                    return None, f"ZIP archive member is encrypted: {item.filename}"
                ratio = item.file_size / max(item.compress_size, 1)
                if item.file_size > 1_000_000 and ratio > max_compression_ratio:
                    return (
                        None,
                        f"ZIP archive member has unsafe compression ratio: {item.filename}",
                    )
            bad_member = archive.testzip()
            if bad_member:
                return None, f"ZIP CRC validation failed for member: {bad_member}"

            members: list[dict[str, object]] = []
            for item in infos:
                digest = hashlib.sha256()
                with archive.open(item) as stream:
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
                members.append(
                    {
                        "name": item.filename,
                        "compressedSize": item.compress_size,
                        "uncompressedSize": item.file_size,
                        "crc32": f"{item.CRC:08x}",
                        "sha256": digest.hexdigest(),
                    }
                )
            return tuple(members), None
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        return None, f"ZIP container validation failed: {type(exc).__name__}."


def validate_source_artifact(
    content: bytes,
    *,
    url: str | None = None,
    response_content_length: int | str | None = None,
    expected_sha256: str | None = None,
    max_archive_members: int = 500,
    max_uncompressed_bytes: int = 512 * 1024 * 1024,
    max_compression_ratio: float = 1_000.0,
) -> ArtifactIntegrityResult:
    content_length = len(content)
    content_hash = hashlib.sha256(content).hexdigest()
    path = urlsplit(url or "").path.lower()
    expected_zip = path.endswith((".zip", ".xlsx"))
    expected_tabular = path.endswith((".csv", ".txt", ".zip", ".xls", ".xlsx"))
    response_matches: bool | None = None
    expected_hash_matches: bool | None = None

    if not content:
        return _result(
            "WAIT_EMPTY_PARSE",
            "Downloaded artifact is empty.",
            content_hash=content_hash,
            content_length=0,
            media_type="application/octet-stream",
            response_length_matches=response_matches,
            expected_hash_matches=expected_hash_matches,
        )

    if response_content_length is not None:
        try:
            declared_length = int(str(response_content_length).strip())
        except ValueError:
            return _result(
                "WAIT_PARSE_ERROR",
                "Response Content-Length is not an integer.",
                content_hash=content_hash,
                content_length=content_length,
                media_type="application/octet-stream",
                response_length_matches=False,
                expected_hash_matches=expected_hash_matches,
            )
        response_matches = declared_length == content_length
        if not response_matches:
            return _result(
                "WAIT_PARSE_ERROR",
                f"Response Content-Length {declared_length} does not match {content_length} downloaded bytes.",
                content_hash=content_hash,
                content_length=content_length,
                media_type="application/octet-stream",
                response_length_matches=False,
                expected_hash_matches=expected_hash_matches,
            )

    if expected_sha256 is not None:
        normalized_hash = expected_sha256.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", normalized_hash):
            return _result(
                "WAIT_PARSE_ERROR",
                "Expected SHA-256 manifest value is invalid.",
                content_hash=content_hash,
                content_length=content_length,
                media_type="application/octet-stream",
                response_length_matches=response_matches,
                expected_hash_matches=False,
            )
        expected_hash_matches = hmac.compare_digest(content_hash, normalized_hash)
        if not expected_hash_matches:
            return _result(
                "WAIT_PARSE_ERROR",
                "Downloaded artifact SHA-256 does not match the supplied manifest.",
                content_hash=content_hash,
                content_length=content_length,
                media_type="application/octet-stream",
                response_length_matches=response_matches,
                expected_hash_matches=False,
            )

    head = content[:1024].lstrip().lower()
    if expected_tabular and (head.startswith(b"<html") or b"<html" in head[:200]):
        return _result(
            "WAIT_SCHEMA_MISMATCH",
            "Expected a data artifact but received HTML content.",
            content_hash=content_hash,
            content_length=content_length,
            media_type="text/html",
            response_length_matches=response_matches,
            expected_hash_matches=expected_hash_matches,
        )

    is_zip = zipfile.is_zipfile(io.BytesIO(content))
    if expected_zip and not is_zip:
        return _result(
            "WAIT_PARSE_ERROR",
            "URL declares a ZIP/XLSX artifact but downloaded bytes are not a valid ZIP container.",
            content_hash=content_hash,
            content_length=content_length,
            media_type="application/octet-stream",
            response_length_matches=response_matches,
            expected_hash_matches=expected_hash_matches,
        )

    if is_zip:
        members, error = _zip_members(
            content,
            max_archive_members=max_archive_members,
            max_uncompressed_bytes=max_uncompressed_bytes,
            max_compression_ratio=max_compression_ratio,
        )
        if error:
            return _result(
                "WAIT_PARSE_ERROR",
                error,
                content_hash=content_hash,
                content_length=content_length,
                media_type="application/zip",
                response_length_matches=response_matches,
                expected_hash_matches=expected_hash_matches,
            )
        return _result(
            "PASS",
            "Artifact hash, response length and ZIP container checks passed.",
            content_hash=content_hash,
            content_length=content_length,
            media_type="application/zip",
            response_length_matches=response_matches,
            expected_hash_matches=expected_hash_matches,
            members=members or (),
        )

    if head.startswith((b"{", b"[")):
        media_type = "application/json"
    elif expected_tabular:
        media_type = "text/tabular"
    else:
        media_type = "application/octet-stream"
    return _result(
        "PASS",
        "Artifact hash and transport-level checks passed.",
        content_hash=content_hash,
        content_length=content_length,
        media_type=media_type,
        response_length_matches=response_matches,
        expected_hash_matches=expected_hash_matches,
    )
