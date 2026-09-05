#!/usr/bin/env python3
"""
Market Data Pipeline — Master Orchestrator
==========================================
Runs the full pipeline: Download → Parse → Feature Engineer

Usage:
    pip install requests pandas openpyxl pdfplumber
    python market_data_pipeline.py

Steps:
    1. Downloads all raw data (CFTC, NSE, BSE, MSE, MCX)
    2. Parses raw files into clean DataFrames
    3. Builds unified feature sets for stock prediction scanner
    4. Saves everything as Parquet files in ./market_data/processed/
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_script(script_name: str):
    """Run a Python script and stream output."""
    script_path = Path(__file__).parent / script_name
    if not script_path.exists():
        print(f"❌ {script_name} not found in {Path(__file__).parent}")
        return False

    print(f"\n{'='*60}")
    print(f"  RUNNING: {script_name}")
    print(f"{'='*60}")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=False,
        text=True
    )
    return result.returncode == 0

def main():
    print("=" * 70)
    print("  MARKET DATA PIPELINE — MASTER ORCHESTRATOR")
    print(f"  Started: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    # Step 1: Download
    success = run_script("market_data_downloader.py")
    if not success:
        print("\n⚠️  Downloader had issues, continuing with available data...")

    # Step 2: Parse
    success = run_script("market_data_parser.py")
    if not success:
        print("\n❌ Parser failed. Check errors above.")
        return

    print("\n" + "=" * 70)
    print("  ✅ PIPELINE COMPLETE")
    print("=" * 70)
    print("\nNext steps for your scanner:")
    print("  1. Load features:  pd.read_parquet('market_data/processed/unified_cftc_sentiment.parquet')")
    print("  2. Load FII/DII:   pd.read_parquet('market_data/processed/unified_india_fiidii.parquet')")
    print("  3. Load OI:        pd.read_parquet('market_data/processed/unified_india_participant_oi.parquet')")
    print("  4. Load MCX:       pd.read_parquet('market_data/processed/unified_mcx_warehouse.parquet')")

if __name__ == "__main__":
    main()
