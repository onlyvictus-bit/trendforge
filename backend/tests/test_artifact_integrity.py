from __future__ import annotations

import hashlib
import io
import zipfile

from trendforge_api.artifact_integrity import validate_source_artifact
from trendforge_api.source_parser import parse_source_content


def _zip_bytes(name: str, content: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, content)
    return buffer.getvalue()


def test_empty_artifact_fails_closed() -> None:
    result = validate_source_artifact(b"", url="https://example.test/file.csv")

    assert result.state == "WAIT_EMPTY_PARSE"
    assert result.content_length == 0


def test_valid_zip_records_container_and_member_lineage() -> None:
    content = _zip_bytes("fo.csv", "SYMBOL,OPEN_INTEREST\nRELIANCE,100\n")

    result = validate_source_artifact(
        content,
        url="https://example.test/fo.csv.zip",
        response_content_length=len(content),
    )

    assert result.state == "PASS"
    assert result.media_type == "application/zip"
    assert result.content_hash == hashlib.sha256(content).hexdigest()
    assert result.response_length_matches is True
    assert len(result.members) == 1
    assert result.members[0]["name"] == "fo.csv"
    assert (
        result.members[0]["sha256"]
        == hashlib.sha256(b"SYMBOL,OPEN_INTEREST\nRELIANCE,100\n").hexdigest()
    )


def test_response_content_length_mismatch_blocks_parser() -> None:
    result = validate_source_artifact(
        b"SYMBOL,OPEN_INTEREST\nRELIANCE,100\n",
        url="https://example.test/file.csv",
        response_content_length=999,
    )

    assert result.state == "WAIT_PARSE_ERROR"
    assert result.response_length_matches is False
    assert "Content-Length" in result.reason


def test_expected_hash_mismatch_blocks_parser() -> None:
    result = validate_source_artifact(
        b"SYMBOL,OPEN_INTEREST\nRELIANCE,100\n",
        url="https://example.test/file.csv",
        expected_sha256="0" * 64,
    )

    assert result.state == "WAIT_PARSE_ERROR"
    assert result.expected_hash_matches is False


def test_zip_path_traversal_is_rejected() -> None:
    content = _zip_bytes("../outside.csv", "SYMBOL,OPEN_INTEREST\nX,1\n")

    result = validate_source_artifact(content, url="https://example.test/file.csv.zip")

    assert result.state == "WAIT_PARSE_ERROR"
    assert "unsafe path" in result.reason.lower()


def test_declared_zip_with_invalid_container_is_rejected() -> None:
    result = validate_source_artifact(
        b"not a zip archive", url="https://example.test/file.csv.zip"
    )

    assert result.state == "WAIT_PARSE_ERROR"
    assert "valid ZIP" in result.reason


def test_html_response_for_csv_url_is_schema_mismatch() -> None:
    result = validate_source_artifact(
        b"<html><body>Access denied</body></html>",
        url="https://example.test/file.csv",
    )

    assert result.state == "WAIT_SCHEMA_MISMATCH"


def test_source_parser_attaches_integrity_lineage_before_udiff_parse() -> None:
    csv_text = (
        "TCKR_SYMB,FIN_INSTRM_TP,XPRY_DT,CLS_PRIC,PRVS_CLSG_PRIC,"
        "UNDRLYG_PRIC,OPN_INTRST,CHNG_IN_OPN_INTRST,TTL_TRADG_VOL\n"
        "RELIANCE,FUTSTK,30-07-2026,3020,3000,2995,120000,5000,25000\n"
    )
    content = _zip_bytes("BhavCopy_NSE_FO.csv", csv_text)

    result = parse_source_content(
        "nse_fo_bhavcopy",
        content,
        url="https://nsearchives.nseindia.com/content/fo/"
        "BhavCopy_NSE_FO_0_0_0_20260710_F_0000.csv.zip",
        response_headers={"content-length": str(len(content))},
    )

    assert result.parser_state == "PARSED_STRUCTURED"
    assert result.output["artifactIntegrity"]["state"] == "PASS"
    assert result.output["artifactIntegrity"]["members"][0]["name"].endswith(".csv")
    assert result.output["rows"][0]["oiQuadrant"] == "LONG_BUILD_UP"


def test_source_parser_blocks_bad_zip_before_udiff_parser() -> None:
    result = parse_source_content(
        "nse_fo_bhavcopy",
        b"not zip",
        url="https://nsearchives.nseindia.com/content/fo/"
        "BhavCopy_NSE_FO_0_0_0_20260710_F_0000.csv.zip",
    )

    assert result.parser_state == "WAIT_PARSE_ERROR"
    assert result.output["artifactIntegrity"]["state"] == "WAIT_PARSE_ERROR"
    assert result.record_count == 0
