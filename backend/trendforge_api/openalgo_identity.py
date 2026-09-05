from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Iterable, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


IDENTITY_SCHEMA_VERSION = "trendforge.openalgo-identity.v1"
SUPPORTED_EXCHANGES = frozenset({"NSE", "NFO", "MCX"})
_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9&._-]{1,80}$")


class InstrumentKind(StrEnum):
    EQUITY = "EQUITY"
    INDEX = "INDEX"
    FUTURE = "FUTURE"
    OPTION = "OPTION"


class IdentityState(StrEnum):
    EXACT = "EXACT"
    WAIT_IDENTITY = "WAIT_IDENTITY"


class OpenAlgoInstrumentContract(BaseModel):
    """One exact, versioned row from an OpenAlgo master contract."""

    model_config = ConfigDict(frozen=True)

    exchange: str
    segment: str
    symbol: str
    broker_symbol: str
    token: str
    name: str
    instrument_kind: InstrumentKind
    expiry: date | None = None
    strike: float | None = Field(default=None, gt=0)
    option_type: str | None = None
    lot_size: int = Field(gt=0)
    tick_size: float = Field(gt=0)
    unit: str
    broker_exchange: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    source_version: str = Field(min_length=1)
    mapping_source: str = "OPENALGO_MASTER_CONTRACT"

    @field_validator("exchange")
    @classmethod
    def validate_exchange(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in SUPPORTED_EXCHANGES:
            raise ValueError("exchange must be NSE, NFO, or MCX")
        return normalized

    @field_validator("symbol", "broker_symbol", "token", "name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("instrument identity text cannot be empty")
        return normalized

    @field_validator("segment", "unit", "mapping_source")
    @classmethod
    def normalize_contract_text(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("instrument contract text cannot be empty")
        return normalized

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        if not _SYMBOL_PATTERN.fullmatch(value):
            raise ValueError("symbol contains unsupported characters")
        return value

    @field_validator("option_type")
    @classmethod
    def normalize_option_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if normalized not in {"CE", "PE"}:
            raise ValueError("option_type must be CE or PE")
        return normalized

    @model_validator(mode="after")
    def validate_contract_shape(self) -> "OpenAlgoInstrumentContract":
        if self.exchange == "NSE" and self.instrument_kind not in {
            InstrumentKind.EQUITY,
            InstrumentKind.INDEX,
        }:
            raise ValueError("NSE identity cannot carry a derivative contract")
        if self.exchange == "NSE" and self.segment not in {"CASH", "INDEX"}:
            raise ValueError("NSE identity requires CASH or INDEX segment")
        if self.exchange in {"NFO", "MCX"} and self.instrument_kind not in {
            InstrumentKind.FUTURE,
            InstrumentKind.OPTION,
        }:
            raise ValueError("NFO and MCX identities must be derivative contracts")
        if self.exchange == "NFO" and self.segment != "DERIVATIVES":
            raise ValueError("NFO identity requires DERIVATIVES segment")
        if self.exchange == "MCX" and self.segment != "COMMODITY_DERIVATIVES":
            raise ValueError("MCX identity requires COMMODITY_DERIVATIVES segment")
        if self.instrument_kind in {InstrumentKind.FUTURE, InstrumentKind.OPTION}:
            if self.expiry is None:
                raise ValueError("derivative identity requires expiry")
        elif self.expiry is not None or self.strike is not None or self.option_type:
            raise ValueError("cash identity cannot carry derivative terms")
        if self.instrument_kind is InstrumentKind.OPTION:
            if self.strike is None or self.option_type is None:
                raise ValueError("option identity requires strike and option_type")
        elif self.strike is not None or self.option_type is not None:
            raise ValueError("non-option identity cannot carry option terms")
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("valid_from cannot be after valid_to")
        return self

    @property
    def canonical_id(self) -> str:
        return f"{self.exchange}:{self.symbol}"


class InstrumentIdentityQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    exchange: str
    symbol: str
    as_of: date
    expected_kind: InstrumentKind | None = None
    expected_expiry: date | None = None
    expected_strike: float | None = Field(default=None, gt=0)
    expected_option_type: str | None = None

    @field_validator("exchange", "symbol")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("expected_option_type")
    @classmethod
    def normalize_expected_option_type(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class InstrumentIdentityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: IdentityState
    reason_code: str
    mapping_version: str
    mapping_hash: str
    query: InstrumentIdentityQuery
    candidate_count: int = Field(ge=0)
    contract: OpenAlgoInstrumentContract | None = None

    @model_validator(mode="after")
    def validate_result(self) -> "InstrumentIdentityResult":
        if self.state is IdentityState.EXACT:
            if self.reason_code != "IDENTITY_EXACT" or self.contract is None:
                raise ValueError("EXACT identity requires one contract")
        elif self.contract is not None:
            raise ValueError("WAIT_IDENTITY cannot expose an accepted contract")
        return self


class OpenAlgoInstrumentMapper:
    """Exact-match NSE/NFO/MCX mapper. It never performs fuzzy fallback."""

    def __init__(
        self,
        contracts: Iterable[OpenAlgoInstrumentContract],
        *,
        mapping_version: str = IDENTITY_SCHEMA_VERSION,
    ) -> None:
        self.mapping_version = mapping_version.strip()
        if not self.mapping_version:
            raise ValueError("mapping_version cannot be empty")
        self.contracts = tuple(contracts)
        if not self.contracts:
            raise ValueError("instrument mapper requires populated master rows")
        self._by_key: dict[tuple[str, str], list[OpenAlgoInstrumentContract]] = {}
        self._by_symbol: dict[str, list[OpenAlgoInstrumentContract]] = {}
        for contract in self.contracts:
            self._by_key.setdefault((contract.exchange, contract.symbol), []).append(
                contract
            )
            self._by_symbol.setdefault(contract.symbol, []).append(contract)
        canonical = [
            contract.model_dump(mode="json")
            for contract in sorted(
                self.contracts,
                key=lambda row: (row.exchange, row.symbol, row.token, row.source_version),
            )
        ]
        payload = json.dumps(
            {"mappingVersion": self.mapping_version, "contracts": canonical},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.mapping_hash = hashlib.sha256(payload).hexdigest()

    @classmethod
    def from_openalgo_master_rows(
        cls,
        rows: Iterable[Mapping[str, Any]],
        *,
        source_version: str,
        mapping_version: str = IDENTITY_SCHEMA_VERSION,
    ) -> "OpenAlgoInstrumentMapper":
        contracts = tuple(
            _contract_from_master_row(row, source_version=source_version)
            for row in rows
        )
        return cls(contracts, mapping_version=mapping_version)

    def resolve(self, query: InstrumentIdentityQuery) -> InstrumentIdentityResult:
        exact = self._by_key.get((query.exchange, query.symbol), [])
        if not exact:
            same_symbol = self._by_symbol.get(query.symbol, [])
            reason = "IDENTITY_CROSS_SEGMENT" if same_symbol else "IDENTITY_UNKNOWN"
            return self._wait(query, reason, len(same_symbol))
        if len(exact) != 1:
            return self._wait(query, "IDENTITY_AMBIGUOUS", len(exact))
        contract = exact[0]
        if contract.valid_from and query.as_of < contract.valid_from:
            return self._wait(query, "IDENTITY_NOT_EFFECTIVE", 1)
        if contract.valid_to and query.as_of > contract.valid_to:
            return self._wait(query, "IDENTITY_EXPIRED", 1)
        if contract.expiry and query.as_of > contract.expiry:
            return self._wait(query, "IDENTITY_EXPIRED", 1)
        expected = (
            (query.expected_kind, contract.instrument_kind),
            (query.expected_expiry, contract.expiry),
            (query.expected_strike, contract.strike),
            (query.expected_option_type, contract.option_type),
        )
        if any(wanted is not None and wanted != actual for wanted, actual in expected):
            return self._wait(query, "IDENTITY_CONTRACT_MISMATCH", 1)
        return InstrumentIdentityResult(
            state=IdentityState.EXACT,
            reason_code="IDENTITY_EXACT",
            mapping_version=self.mapping_version,
            mapping_hash=self.mapping_hash,
            query=query,
            candidate_count=1,
            contract=contract,
        )

    def _wait(
        self, query: InstrumentIdentityQuery, reason: str, candidate_count: int
    ) -> InstrumentIdentityResult:
        return InstrumentIdentityResult(
            state=IdentityState.WAIT_IDENTITY,
            reason_code=reason,
            mapping_version=self.mapping_version,
            mapping_hash=self.mapping_hash,
            query=query,
            candidate_count=candidate_count,
        )


def _parse_expiry(value: Any) -> date | None:
    if value in {None, ""}:
        return None
    text = str(value).strip().upper()
    for fmt in ("%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d", "%d%b%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("master contract expiry uses an unsupported format")


def _contract_from_master_row(
    row: Mapping[str, Any], *, source_version: str
) -> OpenAlgoInstrumentContract:
    exchange = str(row.get("exchange", "")).strip().upper()
    symbol = str(row.get("symbol", "")).strip().upper()
    raw_type = str(row.get("instrumenttype", "")).strip().upper()
    derivative_exchange = exchange in {"NFO", "MCX"}
    if derivative_exchange and (
        symbol.endswith(("CE", "PE")) or "OPT" in raw_type
    ):
        kind = InstrumentKind.OPTION
    elif derivative_exchange and (
        symbol.endswith("FUT") or "FUT" in raw_type
    ):
        kind = InstrumentKind.FUTURE
    elif exchange == "NSE" and "INDEX" in raw_type:
        kind = InstrumentKind.INDEX
    else:
        kind = InstrumentKind.EQUITY
    option_type = symbol[-2:] if kind is InstrumentKind.OPTION else None
    strike_value = row.get("strike")
    strike = float(strike_value) if strike_value not in {None, "", 0, "0"} else None
    return OpenAlgoInstrumentContract(
        exchange=exchange,
        segment=(
            str(row.get("segment")).strip().upper()
            if row.get("segment")
            else (
                "CASH"
                if exchange == "NSE" and kind is InstrumentKind.EQUITY
                else "INDEX"
                if exchange == "NSE"
                else "DERIVATIVES"
                if exchange == "NFO"
                else "COMMODITY_DERIVATIVES"
            )
        ),
        symbol=symbol,
        broker_symbol=str(row.get("brsymbol") or symbol),
        broker_exchange=(str(row.get("brexchange")).strip().upper() or None),
        token=str(row.get("token", "")),
        name=str(row.get("name") or symbol),
        instrument_kind=kind,
        expiry=_parse_expiry(row.get("expiry")),
        strike=strike,
        option_type=option_type,
        lot_size=int(float(row.get("lotsize") or 0)),
        tick_size=float(row.get("tick_size") or 0),
        unit=str(
            row.get("unit")
            or ("SHARE" if exchange == "NSE" else "CONTRACT")
        ),
        source_version=source_version,
        mapping_source=str(row.get("mapping_source") or "OPENALGO_MASTER_CONTRACT"),
    )
