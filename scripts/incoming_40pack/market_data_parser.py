#!/usr/bin/env python3
"""
Unified Market Data Parser for Stock Prediction Scanner
--------------------------------------------------------
Converts all raw downloaded files (CFTC CSVs, NSE JSONs/CSVs, BSE JSONs,
MSE XLSXs, MCX PDFs) into clean, unified Pandas DataFrames ready for
feature engineering and model training.

Usage:
    pip install pandas openpyxl pdfplumber
    python market_data_parser.py

Output:
    ./market_data/processed/
        ├── cftc_unified.parquet
        ├── nse_fiidii.parquet
        ├── nse_participant_oi.parquet
        ├── nse_fii_derivatives.parquet
        ├── bse_participant_oi.parquet
        ├── bse_fiidii.parquet
        ├── mse_participant_oi.parquet
        └── mcx_stock_position.parquet
"""

import os
import re
import json
import glob
import warnings
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

BASE = Path("market_data")
PROCESSED = BASE / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# 1. CFTC PARSER
# ═══════════════════════════════════════════════════════════════

def parse_cftc(year: int = 2026) -> pd.DataFrame:
    """
    Parse all CFTC ZIP extracts into a unified DataFrame.
    Handles: Disaggregated, Legacy, TFF, CIT reports.
    """
    cftc_dir = BASE / "cftc" / str(year) / "extracted"
    if not cftc_dir.exists():
        print(f"  ⚠️  CFTC extracted dir not found: {cftc_dir}")
        return pd.DataFrame()

    all_dfs = []
    txt_files = list(cftc_dir.glob("*.txt"))
    print(f"  Found {len(txt_files)} CFTC text files")

    for fpath in txt_files:
        try:
            df = pd.read_csv(fpath, low_memory=False)
            # Add source metadata
            fname = fpath.name.lower()
            if "disagg" in fname:
                df["report_type"] = "disaggregated"
            elif "fin" in fname or "tff" in fname:
                df["report_type"] = "tff"
            elif "cit" in fname:
                df["report_type"] = "cit"
            else:
                df["report_type"] = "legacy"

            df["fut_or_combined"] = "combined" if "com" in fname else "futures_only"
            df["source_file"] = fpath.name
            all_dfs.append(df)
            print(f"    ✅ {fpath.name}: {len(df)} rows x {len(df.columns)} cols")
        except Exception as e:
            print(f"    ❌ {fpath.name}: {e}")

    if not all_dfs:
        return pd.DataFrame()

    # Combine all reports
    df_all = pd.concat(all_dfs, ignore_index=True)

    # Standardize key columns
    df_all["date"] = pd.to_datetime(df_all["Report_Date_as_YYYY-MM-DD"], errors="coerce")
    df_all["commodity"] = df_all["Market_and_Exchange_Names"].astype(str)
    df_all["cftc_code"] = df_all["CFTC_Contract_Market_Code"].astype(str)

    # Select scanner-relevant columns
    core_cols = [
        "date", "commodity", "cftc_code", "report_type", "fut_or_combined",
        "Open_Interest_All",
        "Prod_Merc_Positions_Long_All", "Prod_Merc_Positions_Short_All",
        "M_Money_Positions_Long_All", "M_Money_Positions_Short_All",
        "Swap_Positions_Long_All", "Swap__Positions_Short_All",
        "Other_Rept_Positions_Long_All", "Other_Rept_Positions_Short_All",
        "Tot_Rept_Positions_Long_All", "Tot_Rept_Positions_Short_All",
        "NonRept_Positions_Long_All", "NonRept_Positions_Short_All",
    ]

    # Only keep columns that exist
    keep_cols = [c for c in core_cols if c in df_all.columns]
    df_out = df_all[keep_cols].copy()

    # Compute net positions (long - short) for each category
    for prefix in ["Prod_Merc", "M_Money", "Swap", "Other_Rept", "Tot_Rept", "NonRept"]:
        long_col = f"{prefix}_Positions_Long_All"
        short_col = f"{prefix}_Positions_Short_All"
        if long_col in df_out.columns and short_col in df_out.columns:
            df_out[f"{prefix}_Net"] = df_out[long_col] - df_out[short_col]

    # Compute COT Index (0-100) for Managed Money
    if "M_Money_Positions_Long_All" in df_out.columns and "M_Money_Positions_Short_All" in df_out.columns:
        df_out["MM_Net"] = df_out["M_Money_Positions_Long_All"] - df_out["M_Money_Positions_Short_All"]
        # Group by commodity to compute rolling min/max
        df_out["MM_Net_52w_min"] = df_out.groupby("commodity")["MM_Net"].transform(
            lambda x: x.rolling(52, min_periods=1).min()
        )
        df_out["MM_Net_52w_max"] = df_out.groupby("commodity")["MM_Net"].transform(
            lambda x: x.rolling(52, min_periods=1).max()
        )
        denom = df_out["MM_Net_52w_max"] - df_out["MM_Net_52w_min"]
        df_out["COT_Index_MM"] = np.where(
            denom != 0,
            100 * (df_out["MM_Net"] - df_out["MM_Net_52w_min"]) / denom,
            50
        )

    print(f"  ✅ CFTC unified: {len(df_out)} rows x {len(df_out.columns)} cols")
    return df_out


# ═══════════════════════════════════════════════════════════════
# 2. NSE PARSERS
# ═══════════════════════════════════════════════════════════════

def parse_nse_fiidii() -> pd.DataFrame:
    """Parse NSE FII/DII cash activity JSON files."""
    src_dir = BASE / "nse" / "fii_dii"
    if not src_dir.exists():
        return pd.DataFrame()

    all_records = []
    for fpath in sorted(src_dir.glob("fiidii_*.json")):
        try:
            data = json.loads(fpath.read_text())
            date_str = fpath.stem.split("_")[-1]
            date = pd.to_datetime(date_str, format="%Y%m%d")
            for rec in data.get("data", []):
                rec["date"] = date
                rec["source"] = "NSE"
                all_records.append(rec)
        except Exception as e:
            print(f"    ❌ {fpath.name}: {e}")

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    # Standardize column names
    rename_map = {
        "category": "investor_type",
        "buyValue": "buy_value_cr",
        "sellValue": "sell_value_cr",
        "netValue": "net_value_cr",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Convert numeric strings to floats
    for col in ["buy_value_cr", "sell_value_cr", "net_value_cr"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    print(f"  ✅ NSE FII/DII: {len(df)} rows")
    return df


def parse_nse_participant_oi() -> pd.DataFrame:
    """Parse NSE F&O Participant-wise OI CSV archives."""
    src_dir = BASE / "nse" / "participant_oi"
    if not src_dir.exists():
        return pd.DataFrame()

    all_dfs = []
    for fpath in sorted(src_dir.glob("fao_participant_oi_*.csv")):
        try:
            df = pd.read_csv(fpath)
            date_str = fpath.stem.split("_")[-1]
            df["date"] = pd.to_datetime(date_str, format="%Y%m%d")
            df["source"] = "NSE"
            all_dfs.append(df)
        except Exception as e:
            print(f"    ❌ {fpath.name}: {e}")

    if not all_dfs:
        return pd.DataFrame()

    df = pd.concat(all_dfs, ignore_index=True)
    # Standardize participant type column
    if "Client Type" in df.columns:
        df = df.rename(columns={"Client Type": "participant_type"})
    elif "CLIENT TYPE" in df.columns:
        df = df.rename(columns={"CLIENT TYPE": "participant_type"})

    print(f"  ✅ NSE Participant OI: {len(df)} rows x {len(df.columns)} cols")
    return df


def parse_nse_fii_derivatives() -> pd.DataFrame:
    """Parse NSE FII Derivatives Statistics CSV archives."""
    src_dir = BASE / "nse" / "fii_derivatives"
    if not src_dir.exists():
        return pd.DataFrame()

    all_dfs = []
    for fpath in sorted(src_dir.glob("fao_participant_fii_*.csv")):
        try:
            df = pd.read_csv(fpath)
            date_str = fpath.stem.split("_")[-1]
            df["date"] = pd.to_datetime(date_str, format="%Y%m%d")
            df["source"] = "NSE"
            all_dfs.append(df)
        except Exception as e:
            print(f"    ❌ {fpath.name}: {e}")

    if not all_dfs:
        return pd.DataFrame()

    df = pd.concat(all_dfs, ignore_index=True)
    print(f"  ✅ NSE FII Derivatives: {len(df)} rows x {len(df.columns)} cols")
    return df


# ═══════════════════════════════════════════════════════════════
# 3. BSE PARSERS
# ═══════════════════════════════════════════════════════════════

def parse_bse_participant_oi() -> pd.DataFrame:
    """Parse BSE Derivatives Participant-wise OI JSON/HTML files."""
    src_dir = BASE / "bse" / "participant_oi"
    if not src_dir.exists():
        return pd.DataFrame()

    all_records = []
    for fpath in sorted(src_dir.glob("participant_oi_*.json")):
        try:
            data = json.loads(fpath.read_text())
            date_str = fpath.stem.split("_")[-1]
            date = pd.to_datetime(date_str, format="%Y%m%d")

            # BSE JSON structure varies; handle common patterns
            if isinstance(data, list):
                for rec in data:
                    rec["date"] = date
                    rec["source"] = "BSE"
                    all_records.append(rec)
            elif isinstance(data, dict):
                if "Table" in data:
                    for rec in data["Table"]:
                        rec["date"] = date
                        rec["source"] = "BSE"
                        all_records.append(rec)
                else:
                    data["date"] = date
                    data["source"] = "BSE"
                    all_records.append(data)
        except Exception as e:
            print(f"    ❌ {fpath.name}: {e}")

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    print(f"  ✅ BSE Participant OI: {len(df)} rows x {len(df.columns)} cols")
    return df


def parse_bse_fiidii() -> pd.DataFrame:
    """Parse BSE FII/DII cash activity JSON files."""
    src_dir = BASE / "bse" / "fii_dii"
    if not src_dir.exists():
        return pd.DataFrame()

    all_records = []
    for fpath in sorted(src_dir.glob("fiidii_*.json")):
        try:
            data = json.loads(fpath.read_text())
            date_str = fpath.stem.split("_")[-1]
            date = pd.to_datetime(date_str, format="%Y%m%d")

            if isinstance(data, list):
                for rec in data:
                    rec["date"] = date
                    rec["source"] = "BSE"
                    all_records.append(rec)
            elif isinstance(data, dict):
                if "Table" in data:
                    for rec in data["Table"]:
                        rec["date"] = date
                        rec["source"] = "BSE"
                        all_records.append(rec)
                else:
                    data["date"] = date
                    data["source"] = "BSE"
                    all_records.append(data)
        except Exception as e:
            print(f"    ❌ {fpath.name}: {e}")

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    print(f"  ✅ BSE FII/DII: {len(df)} rows x {len(df.columns)} cols")
    return df


# ═══════════════════════════════════════════════════════════════
# 4. MSE PARSER
# ═══════════════════════════════════════════════════════════════

def parse_mse_participant_oi() -> pd.DataFrame:
    """Parse MSE Participant-wise OI XLSX files."""
    src_dir = BASE / "mse" / "participant_oi"
    if not src_dir.exists():
        return pd.DataFrame()

    all_dfs = []
    for fpath in sorted(src_dir.glob("participant_oi_*.xlsx")):
        try:
            # MSE files often have header rows; skip first few
            df = pd.read_excel(fpath, header=None)
            # Detect header row (usually row 2 or 3)
            header_row = None
            for i in range(min(5, len(df))):
                row_vals = df.iloc[i].astype(str).str.lower()
                if any("participant" in v or "client" in v or "long" in v for v in row_vals):
                    header_row = i
                    break
            if header_row is not None:
                df = pd.read_excel(fpath, header=header_row)

            date_str = fpath.stem.split("_")[-1]
            df["date"] = pd.to_datetime(date_str, format="%Y%m%d")
            df["source"] = "MSE"
            all_dfs.append(df)
        except Exception as e:
            print(f"    ❌ {fpath.name}: {e}")

    if not all_dfs:
        return pd.DataFrame()

    df = pd.concat(all_dfs, ignore_index=True)
    print(f"  ✅ MSE Participant OI: {len(df)} rows x {len(df.columns)} cols")
    return df


# ═══════════════════════════════════════════════════════════════
# 5. MCX PARSER
# ═══════════════════════════════════════════════════════════════

def parse_mcx_pdfs() -> pd.DataFrame:
    """
    Parse MCX warehouse stock position PDFs into structured data.
    Requires: pip install pdfplumber
    """
    src_dir = BASE / "mcx" / "stock_position_pdfs"
    if not src_dir.exists():
        return pd.DataFrame()

    try:
        import pdfplumber
    except ImportError:
        print("  ⚠️  pdfplumber not installed. Run: pip install pdfplumber")
        return pd.DataFrame()

    all_records = []
    for fpath in sorted(src_dir.glob("mcx_stock_*.pdf")):
        try:
            date_match = re.search(r"mcx_stock_(\d{2}-\d{2}-\d{4})", fpath.name)
            pdf_date = pd.to_datetime(date_match.group(1), format="%d-%m-%Y") if date_match else None

            with pdfplumber.open(fpath) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        # First row as header
                        headers = [str(h).strip().replace("\n", " ") if h else f"col_{i}" 
                                   for i, h in enumerate(table[0])]
                        for row in table[1:]:
                            rec = dict(zip(headers, row))
                            rec["pdf_date"] = pdf_date
                            rec["pdf_file"] = fpath.name
                            rec["source"] = "MCX"
                            all_records.append(rec)
            print(f"    ✅ {fpath.name}: extracted {len(all_records)} records so far")
        except Exception as e:
            print(f"    ❌ {fpath.name}: {e}")

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    print(f"  ✅ MCX Stock Position: {len(df)} rows x {len(df.columns)} cols")
    return df


# ═══════════════════════════════════════════════════════════════
# 6. UNIFIED FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════

def build_unified_features(
    cftc_df: pd.DataFrame,
    nse_fii: pd.DataFrame,
    nse_oi: pd.DataFrame,
    nse_fii_der: pd.DataFrame,
    bse_oi: pd.DataFrame,
    bse_fii: pd.DataFrame,
    mse_oi: pd.DataFrame,
    mcx_df: pd.DataFrame,
) -> Dict[str, pd.DataFrame]:
    """
    Build unified feature sets from all parsed data.
    Returns a dict of DataFrames keyed by use-case.
    """
    features = {}

    # ── A. CFTC Sentiment Features ──
    if not cftc_df.empty:
        cftc_feat = cftc_df.copy()
        # Keep only latest date per commodity for scanner snapshot
        cftc_latest = cftc_feat.sort_values("date").groupby("commodity").last().reset_index()
        features["cftc_sentiment"] = cftc_latest
        print(f"  📊 CFTC sentiment snapshot: {len(cftc_latest)} commodities")

    # ── B. India FII/DII Unified ──
    india_fii = pd.concat([
        nse_fii.assign(exchange="NSE") if not nse_fii.empty else pd.DataFrame(),
        bse_fii.assign(exchange="BSE") if not bse_fii.empty else pd.DataFrame(),
    ], ignore_index=True)
    if not india_fii.empty:
        features["india_fiidii"] = india_fii
        print(f"  📊 India FII/DII unified: {len(india_fii)} rows")

    # ── C. India Participant OI Unified ──
    india_oi = pd.concat([
        nse_oi.assign(exchange="NSE") if not nse_oi.empty else pd.DataFrame(),
        bse_oi.assign(exchange="BSE") if not bse_oi.empty else pd.DataFrame(),
        mse_oi.assign(exchange="MSE") if not mse_oi.empty else pd.DataFrame(),
    ], ignore_index=True)
    if not india_oi.empty:
        features["india_participant_oi"] = india_oi
        print(f"  📊 India Participant OI unified: {len(india_oi)} rows")

    # ── D. MCX Warehouse Stock ──
    if not mcx_df.empty:
        features["mcx_warehouse"] = mcx_df
        print(f"  📊 MCX warehouse: {len(mcx_df)} records")

    return features


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  UNIFIED MARKET DATA PARSER")
    print(f"  Run time: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    # 1. CFTC
    print("
[1/5] Parsing CFTC...")
    cftc_df = parse_cftc()
    if not cftc_df.empty:
        cftc_df.to_parquet(PROCESSED / "cftc_unified.parquet", index=False)

    # 2. NSE
    print("
[2/5] Parsing NSE...")
    nse_fii = parse_nse_fiidii()
    if not nse_fii.empty:
        nse_fii.to_parquet(PROCESSED / "nse_fiidii.parquet", index=False)

    nse_oi = parse_nse_participant_oi()
    if not nse_oi.empty:
        nse_oi.to_parquet(PROCESSED / "nse_participant_oi.parquet", index=False)

    nse_fii_der = parse_nse_fii_derivatives()
    if not nse_fii_der.empty:
        nse_fii_der.to_parquet(PROCESSED / "nse_fii_derivatives.parquet", index=False)

    # 3. BSE
    print("
[3/5] Parsing BSE...")
    bse_oi = parse_bse_participant_oi()
    if not bse_oi.empty:
        bse_oi.to_parquet(PROCESSED / "bse_participant_oi.parquet", index=False)

    bse_fii = parse_bse_fiidii()
    if not bse_fii.empty:
        bse_fii.to_parquet(PROCESSED / "bse_fiidii.parquet", index=False)

    # 4. MSE
    print("
[4/5] Parsing MSE...")
    mse_oi = parse_mse_participant_oi()
    if not mse_oi.empty:
        mse_oi.to_parquet(PROCESSED / "mse_participant_oi.parquet", index=False)

    # 5. MCX
    print("
[5/5] Parsing MCX PDFs...")
    mcx_df = parse_mcx_pdfs()
    if not mcx_df.empty:
        mcx_df.to_parquet(PROCESSED / "mcx_stock_position.parquet", index=False)

    # 6. Build unified features
    print("
" + "=" * 70)
    print("  BUILDING UNIFIED FEATURE SETS")
    print("=" * 70)
    features = build_unified_features(
        cftc_df, nse_fii, nse_oi, nse_fii_der,
        bse_oi, bse_fii, mse_oi, mcx_df
    )

    # Save unified features
    for name, df in features.items():
        fpath = PROCESSED / f"unified_{name}.parquet"
        df.to_parquet(fpath, index=False)
        print(f"  💾 Saved: {fpath.name} ({len(df)} rows x {len(df.columns)} cols)")

    # Summary
    print("
" + "=" * 70)
    print("  DONE — All processed files saved to ./market_data/processed/")
    print("=" * 70)
    print("
Processed outputs:")
    for f in sorted(PROCESSED.glob("*.parquet")):
        sz = f.stat().st_size
        print(f"  {f.name:45s} {sz:>10,} bytes")


if __name__ == "__main__":
    main()


