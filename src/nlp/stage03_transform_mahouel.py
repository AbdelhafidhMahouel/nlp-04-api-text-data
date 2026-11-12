"""stage03_transform_mahouel.py - Stage 03: Transform (custom).

Author: Abdelhafidh Mahouel
Date: 2026-11

Source: validated list of recall records
Sink: Polars DataFrame

Purpose

  Turn openFDA device recall records into an analysis-ready dataset
  for manufacturing quality and continuous improvement (CI) work.

Transformations

  1. Select and rename fields, including nested openfda fields
     (flattening nested JSON with safe .get() access).
  2. Normalize text (collapse whitespace and line breaks).
  3. Map the FDA root cause to a 6M / Ishikawa (fishbone) category:
     Method, Material, Machine, People, Environment, plus Design,
     Software, Labeling & Packaging, and Unknown / Other.
  4. Flag whether the root cause is controllable on the production floor.
  5. Detect failure-mode keywords in the recall reason text.
  6. Calculate word-level text features (reused from Phase 4).
  7. Calculate recall duration in days (a cycle-time measure).
"""

# ============================================================
# Section 1. Setup and Imports
# ============================================================

import logging
from typing import Any

import polars as pl

# ============================================================
# Section 2. Domain Rules (Manufacturing Quality)
# ============================================================

# Ordered rules: the first matching keyword wins.
# Keywords are matched against the lowercase FDA root_cause_description.
ROOT_CAUSE_RULES: list[tuple[str, str]] = [
    ("label", "Labeling & Packaging"),
    ("packag", "Labeling & Packaging"),
    ("software", "Software"),
    ("design", "Design"),
    ("process", "Method"),
    ("change control", "Method"),
    ("reprocess", "Method"),
    ("release of material", "Method"),
    ("expiration", "Method"),
    ("material", "Material"),
    ("component", "Material"),
    ("vendor", "Material"),
    ("counterfeit", "Material"),
    ("equipment", "Machine"),
    ("employee", "People"),
    ("training", "People"),
    ("environment", "Environment"),
    ("storage", "Environment"),
]

# 6M categories a production team can act on directly.
SHOP_FLOOR_CATEGORIES: list[str] = [
    "Method",
    "Material",
    "Machine",
    "People",
    "Environment",
]

# Failure-mode patterns searched in the recall reason text.
FAILURE_MODE_PATTERNS: dict[str, str] = {
    "fm_contamination": r"contaminat|steril|particulate|foreign (?:matter|material)|bioburden|endotoxin",
    "fm_out_of_spec": r"specification|out of spec|tolerance|nonconform|non-conform|dimension|defect",
    "fm_supplier": r"supplier|vendor|third.party|sub-?contract",
    "fm_mechanical": r"crack|break|broke|fractur|leak|detach|loose|separat",
    "fm_electrical_software": r"software|firmware|electrical|battery|circuit|power",
    "fm_labeling": r"label|ifu|instructions for use|mislabel|expiration",
}

WORD_PATTERN: str = r"[A-Za-z0-9']+"


def categorize_root_cause(root_cause: str | None) -> str:
    """Map an FDA root cause description to a 6M-style category.

    Args:
        root_cause (str | None): The FDA root_cause_description value.

    Returns:
        str: The manufacturing quality category.
    """
    if not root_cause:
        return "Unknown / Other"
    text = root_cause.lower()
    for keyword, category in ROOT_CAUSE_RULES:
        if keyword in text:
            return category
    return "Unknown / Other"


# ============================================================
# Section 3. Define Run Transform Function
# ============================================================


def run_transform(
    json_data: list[dict[str, Any]],
    LOG: logging.Logger,
) -> pl.DataFrame:
    """Transform validated recall records into a structured DataFrame.

    Args:
        json_data (list[dict[str, Any]]): Validated recall records.
        LOG (logging.Logger): The logger instance.

    Returns:
        pl.DataFrame: The transformed manufacturing quality dataset.
    """
    LOG.info("========================")
    LOG.info("STAGE 03: TRANSFORM (CUSTOM) starting...")
    LOG.info("========================")

    # ------------------------------------------------------------
    # 1. Select fields and flatten nested openfda values safely
    # ------------------------------------------------------------
    records: list[dict[str, Any]] = []

    for record in json_data:
        openfda = record.get("openfda") or {}
        if not isinstance(openfda, dict):
            openfda = {}

        records.append(
            {
                "recall_event_id": record.get("res_event_number"),
                "recalling_firm": record.get("recalling_firm"),
                "device_name": openfda.get("device_name"),
                "device_class": openfda.get("device_class"),
                "medical_specialty": openfda.get("medical_specialty_description"),
                "recall_status": record.get("recall_status"),
                "root_cause_fda": record.get("root_cause_description"),
                "date_initiated": record.get("event_date_initiated"),
                "date_terminated": record.get("event_date_terminated"),
                "reason_for_recall": record.get("reason_for_recall"),
            }
        )

    df: pl.DataFrame = pl.DataFrame(records, infer_schema_length=None)

    # ------------------------------------------------------------
    # 2. Normalize text: collapse line breaks and repeated spaces
    # ------------------------------------------------------------
    df = df.with_columns(
        pl.col("reason_for_recall")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
        .alias("reason_for_recall")
    )

    # ------------------------------------------------------------
    # 3-4. Root cause category (6M) and shop-floor controllability
    # ------------------------------------------------------------
    df = df.with_columns(
        pl.col("root_cause_fda")
        .map_elements(categorize_root_cause, return_dtype=pl.String)
        .alias("root_cause_category")
    ).with_columns(
        pl.col("root_cause_category")
        .is_in(SHOP_FLOOR_CATEGORIES)
        .alias("shop_floor_controllable")
    )

    # ------------------------------------------------------------
    # 5. Failure-mode keyword flags from the recall reason text
    # ------------------------------------------------------------
    reason_lower = pl.col("reason_for_recall").str.to_lowercase()
    df = df.with_columns(
        [
            reason_lower.str.contains(pattern).alias(name)
            for name, pattern in FAILURE_MODE_PATTERNS.items()
        ]
    )

    # ------------------------------------------------------------
    # 6. Word-level text features (from the Phase 4 modification)
    # ------------------------------------------------------------
    df = df.with_columns(
        [
            pl.col("reason_for_recall")
            .str.count_matches(WORD_PATTERN)
            .alias("reason_word_count"),
            reason_lower.str.extract_all(WORD_PATTERN)
            .list.unique()
            .list.len()
            .alias("reason_unique_word_count"),
        ]
    ).with_columns(
        pl.when(pl.col("reason_word_count") > 0)
        .then(pl.col("reason_unique_word_count") / pl.col("reason_word_count"))
        .otherwise(0.0)
        .round(3)
        .alias("reason_lexical_diversity")
    )

    # ------------------------------------------------------------
    # 7. Recall duration in days (open recalls stay null)
    # ------------------------------------------------------------
    def parse_date(column: str) -> pl.Expr:
        """Parse YYYY-MM-DD or YYYYMMDD strings into dates."""
        text = pl.col(column).cast(pl.String)
        return pl.coalesce(
            text.str.to_date("%Y-%m-%d", strict=False),
            text.str.to_date("%Y%m%d", strict=False),
        )

    df = (
        df.with_columns(
            parse_date("date_initiated").alias("date_initiated"),
            parse_date("date_terminated").alias("date_terminated"),
        )
        .with_columns(
            (pl.col("date_terminated") - pl.col("date_initiated"))
            .dt.total_days()
            .alias("recall_duration_days")
        )
        .sort("date_initiated", descending=True, nulls_last=True)
    )

    # ------------------------------------------------------------
    # Log a short analytical summary
    # ------------------------------------------------------------
    LOG.info("Transformation complete.")
    LOG.info(f"Rows: {df.height}  Columns: {df.width}")

    LOG.info("Recalls by root cause category (Pareto order):")
    pareto = (
        df.group_by("root_cause_category")
        .len()
        .sort("len", descending=True)
        .with_columns(
            (100 * pl.col("len") / pl.col("len").sum()).round(1).alias("pct"),
            (100 * pl.col("len").cum_sum() / pl.col("len").sum())
            .round(1)
            .alias("cum_pct"),
        )
    )
    LOG.info(f"\n{pareto}")

    controllable = df["shop_floor_controllable"].sum()
    LOG.info(f"Shop-floor controllable recalls: {controllable} of {df.height}")

    flags = df.select(list(FAILURE_MODE_PATTERNS)).sum()
    LOG.info(f"Failure-mode keyword counts:\n{flags}")

    LOG.info(f"DataFrame preview:\n{df.head()}")
    LOG.info("Sink: Polars DataFrame created")

    return df
