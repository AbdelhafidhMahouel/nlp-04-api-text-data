# nlp-04-api-text-data

[![Python 3.14](https://img.shields.io/badge/python-3.14%2B-blue?logo=python)](pyproject.toml)
[![CI](https://github.com/AbdelhafidhMahouel/nlp-04-api-text-data/actions/workflows/ci-python-zensical.yml/badge.svg)](https://github.com/AbdelhafidhMahouel/nlp-04-api-text-data/actions/workflows/ci-python-zensical.yml)
[![Documentation](https://img.shields.io/badge/docs-site-blue?logo=github)](https://abdelhafidhmahouel.github.io/nlp-04-api-text-data/)

[![uv managed](https://img.shields.io/badge/uv-managed-DE5FE9)](https://docs.astral.sh/uv/)
[![ty type checked](https://img.shields.io/badge/ty-type_checked-2F80ED)](https://docs.astral.sh/ty/)
[![Zensical docs](https://img.shields.io/badge/Zensical-docs-purple)](https://zensical.org/)
[![MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

> Acquire, validate, and transform JSON data from web APIs using Python,
> applied to manufacturing quality and continuous improvement.

## Project Overview

Author: Abdelhafidh Mahouel

Date: 2026 November

Fourth project in the Web Mining and Applied NLP course.

This project builds an Extract, Validate, Transform, Load (EVTL) pipeline
that retrieves JSON data from a web API, validates its structure,
transforms it into an analysis-ready dataset, and saves the results.

The project was developed in three progressions:

1. **Example** - run the original pipeline on JSONPlaceholder posts.
2. **Phase 4: Technical modification** - add word-level text features
   to the example Transform stage.
3. **Phase 5: New problem** - apply the pipeline to FDA medical device
   recall data for manufacturing root cause and failure-mode analysis.

The original example files are kept as working references.
Custom files use the `_mahouel` suffix.

The project is configured in
[pyproject.toml](pyproject.toml).

## Phase 4: Technical Modification

**File changed:** [src/nlp/stage03_transform.py](src/nlp/stage03_transform.py)

The example measured text only by character length.
Five word-level features were added to describe text structure:

| Feature | Meaning |
| --- | --- |
| `title_word_count` | Number of words in the title |
| `body_word_count` | Number of words in the body |
| `body_unique_word_count` | Number of distinct lowercase words in the body |
| `body_lexical_diversity` | Unique words / total words (0 to 1) |
| `body_avg_word_length` | Average characters per word |

Words are matched with a regular expression,
ratio features are protected against division by zero,
and a statistical summary of the new features is logged on each run.

**Prediction:** adding word-level features would add five columns
without changing the existing ones.

**Result:** the prediction held. The output grew from 6 to 11 columns
for all 100 posts with no missing values.
Bodies averaged 23.85 words and 5.78 characters per word,
and lexical diversity averaged 0.912 (range 0.731 to 1.0),
which reflects the low repetition of generated placeholder text.

## Phase 5: Manufacturing Quality Application

### Problem

Every medical device recall is a manufacturing quality failure
that reached the field.
The FDA records a narrative reason for each recall and assigns a root cause.
This project uses that data to answer:

- Which root causes drive recalls (Pareto analysis)?
- How many recalls are controllable on the production floor?
- Which failure modes appear in the recall reason text?
- How long do recalls stay open (corrective action cycle time)?

### Data

Data comes from the
[openFDA Device Recall API](https://open.fda.gov/apis/device/recall/)
(U.S. Food and Drug Administration),
which is public and requires no API key.

The pipeline requests the 200 most recent recall records:

```text
https://api.fda.gov/device/recall.json?sort=event_date_initiated:desc&limit=200
```

### How the JSON Differs from the Example

| Example (JSONPlaceholder) | Custom (openFDA) |
| --- | --- |
| Top level is a list of records | Top level is a dictionary with `meta` and `results` |
| Flat records | Records contain a nested `openfda` dictionary |
| Every field always present | Fields can be missing (for example, `event_date_terminated`) |
| One record per post | One recall event can span several product records |

### Custom Files

- [src/nlp/config_mahouel.py](src/nlp/config_mahouel.py) - openFDA API URL, User-Agent header, and custom output file names.
- [src/nlp/stage02_validate_mahouel.py](src/nlp/stage02_validate_mahouel.py) - validates the dictionary structure, logs a field-presence data quality report, and excludes records without recall text.
- [src/nlp/stage03_transform_mahouel.py](src/nlp/stage03_transform_mahouel.py) - flattens nested fields, normalizes text, and engineers manufacturing quality features.
- [src/nlp/pipeline_api_json_mahouel.py](src/nlp/pipeline_api_json_mahouel.py) - runs the custom pipeline (Extract and Load stages are reused unchanged).
- [tests/test_mahouel.py](tests/test_mahouel.py) - 12 offline tests for the custom stages.

### Transformations and Derived Features

| Feature | Description |
| --- | --- |
| `device_name`, `device_class`, `medical_specialty` | Flattened from the nested `openfda` dictionary using safe `.get()` access |
| `reason_for_recall` | Recall text with line breaks and extra spaces normalized |
| `root_cause_category` | FDA root cause mapped to a 6M / Ishikawa (fishbone) category: Method, Material, Machine, People, Environment, Design, Software, Labeling & Packaging, Unknown / Other |
| `shop_floor_controllable` | True when the cause is Method, Material, Machine, People, or Environment |
| `fm_contamination`, `fm_out_of_spec`, `fm_supplier`, `fm_mechanical`, `fm_electrical_software`, `fm_labeling` | Failure-mode keyword flags detected in the recall text |
| `reason_word_count`, `reason_unique_word_count`, `reason_lexical_diversity` | Word-level text features reused from Phase 4 |
| `recall_duration_days` | Days from initiation to termination (null while a recall is open) |

### Results

The API reported 59,705 total recall records; the pipeline processed
the 200 most recent, with no records excluded by validation.
The output is a 200-row, 22-column dataset.

Recalls by root cause category (Pareto order):

| Category | Recalls | Percent | Cumulative |
| --- | ---: | ---: | ---: |
| Method | 75 | 37.5% | 37.5% |
| Unknown / Other | 61 | 30.5% | 68.0% |
| Material | 19 | 9.5% | 77.5% |
| Software | 18 | 9.0% | 86.5% |
| Labeling & Packaging | 12 | 6.0% | 92.5% |
| Machine | 11 | 5.5% | 98.0% |
| Design | 4 | 2.0% | 100.0% |

Failure modes found in the recall text:

| Failure mode | Recalls |
| --- | ---: |
| Out of specification | 69 |
| Mechanical | 22 |
| Contamination | 20 |
| Electrical / software | 19 |
| Labeling | 18 |
| Supplier | 0 |

### Interpretation

- **Process (Method) is the leading root cause** at 37.5% of recalls.
- **52.5% of recalls (105 of 200) are controllable on the production floor**
  (Method, Material, Machine), so many field failures trace back to
  process control and incoming materials rather than product design.
- **Out-of-specification** language is the most common failure mode
  in the recall text.

### Limitations

- 30.5% of recent recalls are Unknown / Other because many are still
  under investigation by the firm.
- None of the 200 most recent recalls had a termination date,
  so recall duration cannot be measured yet. A query for closed recalls
  would be needed for cycle-time analysis.
- One recall event can appear as several rows (one per product),
  so counts represent product records, not unique recall events.
- Keyword flags are rule-based and can miss synonyms or
  match words out of context.

## Approach

The project uses a modular Python pipeline
to acquire, validate, transform, and save API data.

- **Extract** - retrieve JSON data from an API and save the raw response.
- **Validate** - verify the JSON structure, record types, and required fields.
- **Transform** - flatten, normalize, and calculate derived features.
- **Load** - save the processed data to a CSV file.

The project uses Requests for HTTP acquisition
and Polars for tabular data processing.

Example project components (kept as working references):

- [src/nlp/pipeline_api_json.py](src/nlp/pipeline_api_json.py) - example EVTL pipeline orchestrator.
- [src/nlp/config.py](src/nlp/config.py) - example API and path configuration.
- [src/nlp/stage01_extract.py](src/nlp/stage01_extract.py) - retrieve API data (shared).
- [src/nlp/stage02_validate.py](src/nlp/stage02_validate.py) - example validation.
- [src/nlp/stage03_transform.py](src/nlp/stage03_transform.py) - example transform with the Phase 4 modification.
- [src/nlp/stage04_load.py](src/nlp/stage04_load.py) - save processed results (shared).
- [tests/](tests/) - automated tests.
- [.github/workflows/](.github/workflows/) - automated testing and documentation deployment.
- [docs/](docs/) - project documentation.
- [zensical.toml](zensical.toml) - documentation configuration.

## Run the Project

Follow the [Professional Python Workflow Guide](https://denisecase.github.io/pro-analytics-02/)
to set up your machine and project environment.

From a VS Code terminal in the project root:

Run the custom manufacturing quality pipeline (Phase 5):

```shell
uv run python -m nlp.pipeline_api_json_mahouel
```

Run the example pipeline with the Phase 4 modification:

```shell
uv run python -m nlp.pipeline_api_json
```

Successful execution produces:

```shell
========================
Pipeline executed successfully!
========================
```

## Output Files

- `project.log` - pipeline execution log.
- `data/raw/case_raw.json` - example API response (JSONPlaceholder posts).
- `data/processed/case_processed.csv` - example dataset with Phase 4 features.
- `data/raw/mahouel_device_recalls_raw.json` - openFDA API response.
- `data/processed/mahouel_device_recalls_processed.csv` - manufacturing quality dataset.

## Verification

Run the automated tests (example tests and custom tests):

```shell
uv run python -m pytest
```

All 14 tests pass (2 example tests and 12 custom tests).

## Project Documentation

The [hosted documentation site](https://abdelhafidhmahouel.github.io/nlp-04-api-text-data/)
is published using Zensical and GitHub Pages.

The documentation site is used to present the project report,
covering such sections as data, methods, results, visualizations,
interpretation, and conclusions.

## CI/CD and GitHub Actions

This project includes continuous integration and continuous deployment (CI/CD)
to check project files and publish the docs.

GitHub Actions include:

- [CI: Python and Documentation Checks](https://github.com/AbdelhafidhMahouel/nlp-04-api-text-data/actions/workflows/ci-python-zensical.yml)
- [CD: Documentation Deployment](https://github.com/AbdelhafidhMahouel/nlp-04-api-text-data/actions/workflows/deploy-zensical.yml)

## Developer Reference

Follow the
[Professional Python Workflow Guide](https://denisecase.github.io/pro-analytics-02/)
for **detailed instructions and troubleshooting**.

### Initialize and Update the Python Environment

With the project open in VS Code, open a VS Code terminal.
Paste each command and hit Enter or Return after to run it.

```shell
uvx pup-clean --delete
uv self update
uv python pin 3.14
uv python install
uv lock --upgrade
uv sync
uv audit
```

### Set Up and Run Git Hooks

Set up and run the git hooks to perform
basic checks automatically before
any changes get pushed to GitHub.

In the VS Code terminal,
paste each command and hit Enter or Return after to run it.

```shell
uvx prek install --force
uvx prek update --freeze --cooldown-days 7

git add -A
uvx prek run --all-files
# repeat if changes were made
uvx prek run --all-files
```

### Run Common Chores

Run linters, formatters, type checks, tests, and
build the documentation.

```shell
uv run ruff check . --fix
uv run ruff format .

uv run ty check
uv run python -m pytest
uv run python -m zensical build
```

### Git add-commit-push to GitHub

After making useful changes, save your work to GitHub.

```shell
git add -A
git commit -m "describe your changes in quotes"
git push -u origin main
```

## Developer Notes

- Use the **UP ARROW** and **DOWN ARROW** in the terminal to scroll through past commands.
- Use `CTRL+f` to find (and replace) text within a file.

## Developer Tools

This project uses professional Python tools to support development,
testing, documentation, and code quality.

- [uv](https://docs.astral.sh/uv/) - Python environments and dependencies.
- [Ruff](https://docs.astral.sh/ruff/) - Python linting and formatting, configured in [.ruff.toml](.ruff.toml).
- [ty](https://docs.astral.sh/ty/) - Python type checking.
- [pytest](https://docs.pytest.org/) - automated Python testing, configured in [.pytest.toml](.pytest.toml).
- [prek](https://prek.j178.dev/) - Git hooks and automated checks, configured in [prek.toml](prek.toml).
- [Zensical](https://zensical.org/) - project documentation, configured in [zensical.toml](zensical.toml).

## Links

- [Hosted Documentation](https://abdelhafidhmahouel.github.io/nlp-04-api-text-data/)
- [Professional Python Workflow Guide](https://denisecase.github.io/pro-analytics-02/)
- [Citation](CITATION.cff)
- [License](LICENSE)
