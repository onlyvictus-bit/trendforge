from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, model_validator


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "config.yaml"


class ScreeningConfig(BaseModel):
    bull_threshold: float = 1.5
    bear_threshold: float = -1.5
    neutral_zone: float = Field(default=0.8, ge=0)
    min_volume_lacs: float = Field(default=10.0, ge=0)
    max_pledge_pct: float = Field(default=30.0, ge=0, le=100)
    min_fii_net_crs: float = 5.0
    min_factor_coverage: float = Field(default=1.0, gt=0, le=1)
    min_direction_probability: float = Field(default=0.70, ge=0.5, le=1)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "ScreeningConfig":
        if self.bear_threshold >= -self.neutral_zone:
            raise ValueError("bear_threshold must be below the neutral zone")
        if self.bull_threshold <= self.neutral_zone:
            raise ValueError("bull_threshold must be above the neutral zone")
        return self


class FactorWeights(BaseModel):
    smart_money: float = Field(ge=0)
    trend: float = Field(ge=0)
    volatility: float = Field(ge=0)
    momentum: float = Field(ge=0)
    fundamental: float = Field(ge=0)
    risk: float = Field(ge=0)

    @model_validator(mode="after")
    def weights_must_sum_to_one(self) -> "FactorWeights":
        if abs(sum(self.model_dump().values()) - 1.0) > 1e-9:
            raise ValueError("factor weights must sum to 1.0")
        return self


class InstitutionalRiskConfig(BaseModel):
    account_size: float = Field(default=100_000, gt=0)
    max_position_pct: float = Field(default=0.10, gt=0, le=1)
    kelly_fraction: float = Field(default=0.5, gt=0, le=1)
    stop_loss_atr_mult: float = Field(default=2.0, gt=0)
    var_confidence: float = Field(default=0.95, gt=0.5, lt=1)
    max_open_positions: int = Field(default=3, ge=1)
    max_daily_loss_pct: float = Field(default=0.015, gt=0, le=0.1)
    max_sector_risk_share: float = Field(default=0.30, gt=0, le=1)
    correlation_threshold: float = Field(default=0.70, ge=0, le=1)


class AIConfig(BaseModel):
    hmm_n_components: int = Field(default=4, ge=2, le=12)
    isolation_forest_contamination: float = Field(default=0.05, gt=0, le=0.5)
    ensemble_weights: dict[str, float]
    probability_slope: float = Field(default=1.5, gt=0)

    @model_validator(mode="after")
    def ensemble_weights_must_sum_to_one(self) -> "AIConfig":
        if abs(sum(self.ensemble_weights.values()) - 1.0) > 1e-9:
            raise ValueError("AI ensemble weights must sum to 1.0")
        return self


class APIConfig(BaseModel):
    nse_base: str
    bse_base: str
    amfi_nav: str
    mfapi_base: str
    nsdl_fpi: str


class CacheConfig(BaseModel):
    ttl_seconds: int = Field(default=300, ge=0)
    backend: Literal["sqlite", "disk"] = "sqlite"
    request_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    max_response_bytes: int = Field(default=10_485_760, ge=1024)
    per_host_interval_seconds: float = Field(default=0.35, ge=0, le=10)
    max_retries: int = Field(default=3, ge=1, le=6)
    retry_backoff_seconds: float = Field(default=1.0, ge=0, le=30)
    retry_max_seconds: float = Field(default=30.0, ge=0, le=120)
    retry_jitter_seconds: float = Field(default=0.25, ge=0, le=5)


ALLOWED_ENDPOINT_HOSTS = {
    "api.upstox.com",
    "api.frankfurter.dev",
    "data.gov.in",
    "data.stats.gov.cn",
    "desagri.gov.in",
    "mausam.imd.gov.in",
    "tradestat.commerce.gov.in",
    "www.cdslindia.com",
    "www.cftc.gov",
    "publicreporting.cftc.gov",
    "www.eia.gov",
    "www.fbil.org.in",
    "www.msei.in",
    "www.nseindia.com",
    "archives.nseindia.com",
    "nsearchives.nseindia.com",
    "api.bseindia.com",
    "www.bseindia.com",
    "www.amfiindia.com",
    "api.mfapi.in",
    "fpi.nsdl.co.in",
    "www.fpi.nsdl.co.in",
    "www.equitymaster.com",
    "www.mcxindia.com",
    "en.sge.com.cn",
    "bakerhughesrigcount.gcs-web.com",
    "www.shfe.com.cn",
    "www.usda.gov",
    "www.rbi.org.in",
}

# Some exchanges serve API JSON and the cookie-seeding page from separate,
# explicitly approved first-party hosts. Keep this narrow rather than allowing
# arbitrary cross-host session priming.
ALLOWED_SEED_HOST_PAIRS = {
    ("api.bseindia.com", "www.bseindia.com"),
}


class EndpointContractConfig(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_]+$")
    url_template: str
    response_kind: Literal["json", "text", "html", "binary"]
    purpose: str = Field(min_length=3, max_length=240)
    http_method: Literal["GET", "POST"] = "GET"
    body_kind: Literal["none", "form", "json"] = "none"
    body_parameters: list[str] = Field(default_factory=list)
    requires_nse_session: bool = False
    required_parameters: list[str] = Field(default_factory=list)
    normalized_source_key: str | None = Field(default=None, pattern=r"^[a-z0-9_]+$")
    contract_status: Literal["VERIFIED", "UNVERIFIED_RESEARCH"] = "VERIFIED"
    referer: str | None = None
    seed_url: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0, le=120)
    credential_env: str | None = Field(
        default=None, pattern=r"^[A-Z][A-Z0-9_]{2,63}$"
    )

    @model_validator(mode="after")
    def validate_endpoint_template(self) -> "EndpointContractConfig":
        placeholders = set(re.findall(r"\{([a-z_]+)\}", self.url_template))
        body_parameters = set(self.body_parameters)
        if placeholders & body_parameters:
            raise ValueError("parameters cannot be present in both URL and request body")
        if placeholders | body_parameters != set(self.required_parameters):
            raise ValueError(
                "required_parameters must exactly match URL and body parameters"
            )
        if self.http_method == "GET" and self.body_kind != "none":
            raise ValueError("GET endpoint contracts cannot define a request body")
        if self.http_method == "POST" and self.body_kind == "none":
            raise ValueError("POST endpoint contracts must define form or json body_kind")
        if self.body_kind == "none" and body_parameters:
            raise ValueError("body_parameters require a non-none body_kind")
        probe = self.url_template
        for placeholder in placeholders:
            probe = probe.replace(f"{{{placeholder}}}", "TEST")
        parsed = urlparse(probe)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_ENDPOINT_HOSTS:
            raise ValueError(
                "endpoint URL must use HTTPS on an approved market-data host"
            )
        if self.requires_nse_session and parsed.hostname != "www.nseindia.com":
            raise ValueError(
                "only NSE endpoint contracts may require NSE session seeding"
            )
        if self.referer:
            referer = urlparse(self.referer)
            if referer.scheme != "https" or referer.hostname not in ALLOWED_ENDPOINT_HOSTS:
                raise ValueError("endpoint referer must use an approved HTTPS host")
        if self.seed_url:
            seed = urlparse(self.seed_url)
            if seed.scheme != "https" or seed.hostname not in ALLOWED_ENDPOINT_HOSTS:
                raise ValueError("endpoint seed_url must use an approved HTTPS host")
            if (
                seed.hostname != parsed.hostname
                and (parsed.hostname, seed.hostname) not in ALLOWED_SEED_HOST_PAIRS
            ):
                raise ValueError("endpoint seed_url must use the endpoint host")
        return self


class InstitutionalConfig(BaseModel):
    version: str
    screening: ScreeningConfig
    weights: FactorWeights
    risk: InstitutionalRiskConfig
    ai: AIConfig
    apis: APIConfig
    endpoint_contracts: list[EndpointContractConfig]
    cache: CacheConfig
    config_hash: str = ""

    @model_validator(mode="after")
    def endpoint_keys_must_be_unique(self) -> "InstitutionalConfig":
        keys = [item.key for item in self.endpoint_contracts]
        if len(keys) != len(set(keys)):
            raise ValueError("endpoint contract keys must be unique")
        return self


@lru_cache(maxsize=8)
def load_institutional_config(path: str | Path | None = None) -> InstitutionalConfig:
    config_path = Path(path).expanduser().resolve() if path else DEFAULT_CONFIG_PATH
    raw_bytes = config_path.read_bytes()
    loaded = yaml.safe_load(raw_bytes)
    if not isinstance(loaded, dict):
        raise ValueError(f"Configuration {config_path} must contain a YAML object")
    canonical = json.dumps(loaded, sort_keys=True, separators=(",", ":")).encode()
    loaded["config_hash"] = hashlib.sha256(canonical).hexdigest()
    return InstitutionalConfig.model_validate(loaded)
