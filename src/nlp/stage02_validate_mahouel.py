"""stage02_validate_mahouel.py - Stage 02: Validate (custom).

Author: Abdelhafidh Mahouel
Date: 2026-11

Source: raw JSON object (openFDA Device Recall response)
Sink: validated list of recall records

Purpose

  Inspect the openFDA JSON structure and confirm the data is usable
  for a manufacturing quality analysis.

How this JSON differs from the example

  - The example API returned a LIST of records at the top level.
    openFDA returns a DICTIONARY with "meta" and "results" keys,
    and the records are inside "results".
  - Example records were flat. openFDA records include a nested
    "openfda" dictionary (device name, device class, specialty).
  - Example records always had every key. openFDA records can be
    missing fields, so presence is measured and reported, not assumed.

Validation Rules

  Structure (hard rules - the pipeline stops if broken):
  - top level is a dict containing "results"
  - "results" is a non-empty list of dicts

  Content (record-level rules):
  - records without usable recall text (reason_for_recall) are excluded,
    because text is required for the NLP analysis
  - presence of each expected field is logged as a data quality report
  - at least one usable record must remain
"""

# ============================================================
# Section 1. Setup and Imports
# ============================================================

import logging
from typing import Any

# Field that must contain text for a record to be usable.
REQUIRED_TEXT_FIELD: str = "reason_for_recall"

# Fields expected for the analysis (reported, not required).
EXPECTED_FIELDS: dict[str, type] = {
    "res_event_number": str,
    "recalling_firm": str,
    "reason_for_recall": str,
    "root_cause_description": str,
    "product_description": str,
    "event_date_initiated": str,
    "event_date_terminated": str,
    "recall_status": str,
    "openfda": dict,
}

# ============================================================
# Section 2. Define Run Validate Function
# ============================================================


def run_validate(
    json_data: Any,
    LOG: logging.Logger,
) -> list[dict[str, Any]]:
    """Inspect and validate the openFDA Device Recall JSON structure.

    Args:
        json_data (Any): The raw JSON data from the Extract stage.
        LOG (logging.Logger): The logger instance.

    Returns:
        list[dict[str, Any]]: Recall records that are usable for analysis.

    Raises:
        TypeError: If the top-level structure or records are the wrong type.
        ValueError: If required content is missing.
    """
    LOG.info("========================")
    LOG.info("STAGE 02: VALIDATE (CUSTOM) starting...")
    LOG.info("========================")

    # ============================================================
    # INSPECT TOP-LEVEL STRUCTURE
    # ============================================================

    LOG.info("JSON STRUCTURE INSPECTION:")
    LOG.info(f"Top-level type: {type(json_data).__name__}")

    if not isinstance(json_data, dict):
        raise TypeError("Expected a dictionary with 'meta' and 'results' keys.")

    LOG.info(f"Top-level keys: {list(json_data.keys())}")

    if "error" in json_data:
        raise ValueError(f"API returned an error: {json_data['error']}")

    if "results" not in json_data:
        raise ValueError("Expected a 'results' key in the API response.")

    meta = json_data.get("meta", {})
    total = meta.get("results", {}).get("total") if isinstance(meta, dict) else None
    LOG.info(f"Total matching records reported by API: {total}")

    records = json_data["results"]

    if not isinstance(records, list):
        raise TypeError("Expected 'results' to be a list of records.")

    if len(records) == 0:
        raise ValueError("Expected at least one record in 'results'.")

    if not all(isinstance(record, dict) for record in records):
        raise TypeError("Expected each record in 'results' to be a dictionary.")

    LOG.info(f"Records received: {len(records)}")
    LOG.info(f"Keys in first record: {sorted(records[0].keys())}")

    # ============================================================
    # DATA QUALITY REPORT: FIELD PRESENCE AND TYPES
    # ============================================================

    LOG.info("FIELD PRESENCE REPORT (present with expected type / total):")
    for field, expected_type in EXPECTED_FIELDS.items():
        present = sum(
            1 for record in records if isinstance(record.get(field), expected_type)
        )
        pct = 100 * present / len(records)
        LOG.info(f"  {field:<24} {present:>4}/{len(records)} ({pct:5.1f}%)")

    # ============================================================
    # RECORD-LEVEL VALIDATION
    # ============================================================

    usable: list[dict[str, Any]] = [
        record
        for record in records
        if isinstance(record.get(REQUIRED_TEXT_FIELD), str)
        and record[REQUIRED_TEXT_FIELD].strip() != ""
    ]

    excluded = len(records) - len(usable)
    LOG.info(f"Records excluded (no usable {REQUIRED_TEXT_FIELD}): {excluded}")

    if len(usable) == 0:
        raise ValueError(f"No records contain usable {REQUIRED_TEXT_FIELD} text.")

    LOG.info(f"Validation passed. Usable records: {len(usable)}")
    LOG.info("Sink: validated list of recall records")

    return usable
