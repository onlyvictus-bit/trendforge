from __future__ import annotations

import os

import uvicorn

# Inventory Refresh POSTs /api/market-data/refresh. That route is built only
# when both collector flags are on (same checklist as trendforge_inventory_app).
# Pytest imports trendforge_api.main directly, so default-off stays in tests.
os.environ.setdefault("MARKET_DATA_69_ENABLED", "1")
os.environ.setdefault("MARKET_DATA_69_PROVISIONAL_OVERRIDE", "1")
os.environ.setdefault("MARKET_DATA_69_AUTOSTART", "1")


if __name__ == "__main__":
    uvicorn.run(
        "trendforge_api.main:app",
        host="127.0.0.1",
        port=int(os.getenv("TRENDFORGE_PORT", "8000")),
        reload=False,
    )
