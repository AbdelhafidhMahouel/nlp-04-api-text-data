"""stage03_transform.py.

Author: Abdelhafidh Mahouel
Date: 2026-11

MODIFICATION (Phase 4):
  Added word-level text features to the Transform stage.
  Character counts (title_length, body_length) measure size only.
  Word-level features describe the structure and richness of the text:
  - title_word_count, body_word_count: number of words (tokens)
  - body_unique_word_count: number of distinct lowercase words
  - body_lexical_diversity: unique words / total words (0-1)
  - body_avg_word_length: average characters per word
  These are standard NLP descriptive features used to compare
  verbosity, repetition, and vocabulary across records.

(EDIT YOUR VERSION OF THIS FILE)

Source: validated JSON object
Sink: Polars DataFrame

Purpose

  Transform validated JSON data into a structured format.

Analytical Questions

- Which fields are needed from the JSON data?
- How can records be normalized into tabular form?
- What derived fields would support analysis?

Edit your Python file to:
- extract the fields needed for your analysis,
- normalize records into a consistent structure,
- create any derived fields required.
"""

# ============================================================
# Section 1. Setup and Imports
# ============================================================

import logging
from typing import Any

import polars as pl

# ============================================================
# Section 2. Define Run Transform Function
# ============================================================


def run_transform(
    json_data: list[dict[str, Any]],
    LOG: logging.Logger,
) -> pl.DataFrame:
    """Transform JSON into a structured DataFrame.

    Args:
        json_data (list[dict[str, Any]]): Validated JSON data.
        LOG (logging.Logger): The logger instance.

    Returns:
        pl.DataFrame: The transformed dataset.
    """
    LOG.info("========================")
    LOG.info("STAGE 03: TRANSFORM starting...")
    LOG.info("========================")

    records: list[dict[str, Any]] = []

    for record in json_data:
        records.append(
            {
                "user_id": record["userId"],
                "post_id": record["id"],
                "title": record["title"],
                "body": record["body"],
            }
        )

    df: pl.DataFrame = pl.DataFrame(records)

    # Derived fields (original example): character counts
    df = df.with_columns(
        [
            pl.col("title").str.len_chars().alias("title_length"),
            pl.col("body").str.len_chars().alias("body_length"),
        ]
    )

    # ============================================================
    # MODIFICATION: word-level text features
    # ============================================================
    # A word (token) is any run of letters, digits, or apostrophes.
    # Lowercasing first means "Est" and "est" count as the same word.
    WORD_PATTERN: str = r"[A-Za-z0-9']+"

    df = df.with_columns(
        [
            pl.col("title").str.count_matches(WORD_PATTERN).alias("title_word_count"),
            pl.col("body").str.count_matches(WORD_PATTERN).alias("body_word_count"),
            pl.col("body")
            .str.to_lowercase()
            .str.extract_all(WORD_PATTERN)
            .list.unique()
            .list.len()
            .alias("body_unique_word_count"),
            pl.col("body")
            .str.extract_all(WORD_PATTERN)
            .list.join("")
            .str.len_chars()
            .alias("body_word_chars"),
        ]
    )

    # Ratios are computed from the counts above.
    # pl.when guards against dividing by zero for empty text.
    df = df.with_columns(
        [
            pl.when(pl.col("body_word_count") > 0)
            .then(pl.col("body_unique_word_count") / pl.col("body_word_count"))
            .otherwise(0.0)
            .round(3)
            .alias("body_lexical_diversity"),
            pl.when(pl.col("body_word_count") > 0)
            .then(pl.col("body_word_chars") / pl.col("body_word_count"))
            .otherwise(0.0)
            .round(2)
            .alias("body_avg_word_length"),
        ]
    ).drop("body_word_chars")

    LOG.info("Word-level feature summary:")
    LOG.info(
        f"\n{df.select(['body_word_count', 'body_lexical_diversity', 'body_avg_word_length']).describe()}"
    )

    LOG.info("Transformation complete.")
    LOG.info(f"DataFrame preview:\n{df.head()}")
    LOG.info("Sink: Polars DataFrame created")

    # Return the transformed DataFrame for use in the next stage.
    return df
