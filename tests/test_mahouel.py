"""Offline tests for the custom manufacturing quality EVTL stages.

Author: Abdelhafidh Mahouel
Date: 2026-11
"""

import logging

import pytest

from nlp.stage02_validate_mahouel import run_validate
from nlp.stage03_transform_mahouel import categorize_root_cause, run_transform

LOG = logging.getLogger(__name__)

SAMPLE_RESPONSE = {
    "meta": {"results": {"skip": 0, "limit": 3, "total": 3}},
    "results": [
        {
            "res_event_number": "90001",
            "recalling_firm": "Acme Devices",
            "reason_for_recall": "Sterile barrier\nmay be compromised due to a sealing process defect.",
            "root_cause_description": "Process control",
            "event_date_initiated": "2025-01-10",
            "event_date_terminated": "2025-03-11",
            "recall_status": "Terminated",
            "openfda": {"device_name": "Catheter", "device_class": "2"},
        },
        {
            "res_event_number": "90002",
            "recalling_firm": "Beta Medical",
            "reason_for_recall": "Supplier provided nonconforming tubing out of specification.",
            "root_cause_description": "Nonconforming Material/Component",
            "event_date_initiated": "2025-02-01",
            "recall_status": "Open, Classified",
        },
        {
            "res_event_number": "90003",
            "recalling_firm": "Gamma Inc",
            "reason_for_recall": "",
            "root_cause_description": "Device Design",
        },
    ],
}


def test_validate_returns_usable_records():
    """Records without recall text are excluded."""
    records = run_validate(SAMPLE_RESPONSE, LOG)
    assert len(records) == 2


def test_validate_rejects_list_top_level():
    """openFDA responses must be a dictionary, not a list."""
    with pytest.raises(TypeError):
        run_validate([{"id": 1}], LOG)


@pytest.mark.parametrize(
    ("root_cause", "expected"),
    [
        ("Process control", "Method"),
        ("Nonconforming Material/Component", "Material"),
        ("Equipment maintenance", "Machine"),
        ("Employee error", "People"),
        ("Device Design", "Design"),
        ("Software design", "Software"),
        ("Packaging process control", "Labeling & Packaging"),
        ("Under Investigation by firm", "Unknown / Other"),
        (None, "Unknown / Other"),
    ],
)
def test_categorize_root_cause(root_cause, expected):
    """FDA root causes map to the expected 6M category."""
    assert categorize_root_cause(root_cause) == expected


def test_transform_builds_features():
    """Transform flattens nested fields and calculates features."""
    df = run_transform(run_validate(SAMPLE_RESPONSE, LOG), LOG)
    row = df.filter(df["recall_event_id"] == "90001").row(0, named=True)
    assert row["device_name"] == "Catheter"
    assert row["root_cause_category"] == "Method"
    assert row["shop_floor_controllable"] is True
    assert row["fm_contamination"] is True
    assert row["recall_duration_days"] == 60
    assert "\n" not in row["reason_for_recall"]

    open_row = df.filter(df["recall_event_id"] == "90002").row(0, named=True)
    assert open_row["device_name"] is None
    assert open_row["fm_supplier"] is True
    assert open_row["fm_out_of_spec"] is True
    assert open_row["recall_duration_days"] is None
