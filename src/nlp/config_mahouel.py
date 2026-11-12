"""config_mahouel.py - Custom configuration for the EVTL pipeline.

Author: Abdelhafidh Mahouel
Date: 2026-11

Purpose

  Store configuration values for a manufacturing quality EVTL pipeline.

Custom Problem

  Medical device recalls are manufacturing quality failures that reached
  the field. The FDA records a narrative reason for each recall and assigns
  a root cause category. This project uses that text to ask:

  - Which root causes drive recalls, and how many are controllable
    on the production floor (process, material, machine, people, environment)?
  - What failure modes (contamination, out-of-specification, supplier issues)
    appear in the recall reason text?
  - How long do recalls stay open (a cycle-time view of corrective action)?

Data Source

  openFDA Device Recall API (U.S. Food and Drug Administration).
  Public, no API key required (anonymous limit: 1,000 requests per day).
  Docs: https://open.fda.gov/apis/device/recall/

  The response is a dictionary with two top-level keys:
  - "meta":    dataset metadata (disclaimer, license, result counts)
  - "results": a list of recall records (some fields are nested or missing)
"""

from pathlib import Path

# ============================================================
# API CONFIGURATION
# ============================================================

# The most recent recall events first, limited to keep the raw file
# well under the 2 MB pre-commit file-size limit.
API_URL: str = (
    "https://api.fda.gov/device/recall.json?sort=event_date_initiated:desc&limit=200"
)

HTTP_REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": "mahouel-manufacturing-quality-evtl/1.0",
    "Accept": "application/json",
}

# ============================================================
# PATH CONFIGURATION
# ============================================================

ROOT_PATH: Path = Path.cwd()
DATA_PATH: Path = ROOT_PATH / "data"
RAW_PATH: Path = DATA_PATH / "raw"
PROCESSED_PATH: Path = DATA_PATH / "processed"

RAW_JSON_PATH: Path = RAW_PATH / "mahouel_device_recalls_raw.json"
PROCESSED_CSV_PATH: Path = PROCESSED_PATH / "mahouel_device_recalls_processed.csv"
