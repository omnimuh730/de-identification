# Healthcare Data De-Identification – Overview and Usage

This project de-identifies healthcare datasets using rule-driven, field-level transformations. It supports multiple feeds (Member, Claims, Guiding Care) and now adds Provider CSV de-identification without changing prior HL7/text logic.

## What’s Included
- Orchestration: `main.py` dynamically loads each feed module and runs it with matching input/output folders.
- Modules:
  - `Member.py` – pipe-delimited/HL7-like text data
  - `Claims.py` – pipe-delimited text data
  - `GuidingCare.py` – multiple files via config with skip rules
  - `Provider.py` – NEW: CSV data de-identification (first line header)
- Utilities: `utils.py` – hashing, masking, value changes, pseudonymization, date shifting.
- Configs:
  - `Config/Member/rules.json`
  - `Config/Claims/rules.json`
  - `Config/Guiding Care/rules.json`
  - `Config/Provider/rules.json` – NEW: maps `fedid` to `hash` for all CSVs

## Goals and Guarantees
- Existing HL7/text pipelines and results are unchanged.
- New Provider CSV flow recognizes `.csv`, reads header, applies configured actions, and writes CSV outputs.
- Core de-identification behavior is reused from `utils.py` to ensure consistency.

## Directory Layout (Data In/Out)
- Input
  - `Data/Member`, `Data/Claims`, `Data/Guiding Care`
  - `Data/Provider` (e.g., `Data/Provider/1072025/*.csv`)
- Output (mirrors input structure)
  - `De-Identified/Member`, `De-Identified/Claims`, `De-Identified/Guiding Care`
  - `De-Identified/Provider` (e.g., `De-Identified/Provider/1072025/*.csv`)

## Running
- Run all feeds (Member, Claims, Guiding Care, Provider CSV):
  - `python main.py`
  - You should see a banner for each feed, including “De-identification Process (Provider CSV)” once Provider runs.
- Run only Provider CSV:
  - `python Provider.py`

## What Changed in This Update
- Added Provider CSV support (no changes to HL7/text de-identification):
  - New config: `Config/Provider/rules.json` (case-insensitive column matching; applies to `*.csv`).
  - New module: `Provider.py` (CSV reader/writer, header-driven field mapping, progress printing, recursive discovery under `Data/Provider`).
  - Updated: `main.py` now calls `run_Provider()` after existing feeds.

## Which Data Changes and How (By Feed)

### Provider (CSV) – NEW
- Column(s): `fedid` (any column with header name `fedid`, case-insensitive; files show multiple `fedid` columns in some layouts and each is processed)
- Action: `hash` (via `utils.extract_numbers_and_hash`) – replaces each numeric chunk with deterministic digits derived from SHA-256 of the original chunk; preserves digits count and leaves punctuation intact.
  - Example shape: `12-3456789` → `75-3815618` (illustrative only; deterministic per input).

## Provider CSV Details
- File discovery: Recursively scans `Data/Provider` for `*.csv` and mirrors the relative paths to `De-Identified/Provider`.
- Header-driven mapping: Reads the first row as the header and builds a column→action map from `Config/Provider/rules.json`.
- Matching modes supported in rules:
  - `name`: exact column name match (case-insensitive by default)
  - `match.mode: exact|icontains|regex` to flexibly match variants
- Current Provider rules highlight Tax ID fields:
  - `Config/Provider/rules.json` targets `fedid` by name and also matches common aliases via regex: `taxid`, `tax_id`, `tin`, `fein`, `federal tax id`, `federalid`, `fed id`.
  - All matched columns use the `hash` action so numeric digits change deterministically while formatting remains stable.

### Why `fedid` equals Tax ID (EIN)
- In the Provider CSV headers you shared, `fedid` appears alongside provider identifiers and organizational attributes, and is commonly used to denote the federal tax identifier (EIN).
- To be robust, the config also includes synonyms (TIN/FEIN/etc.) so any dataset using alternate labels is still de-identified correctly.
- Outcome: Any column representing a business Tax ID will be de-identified using the same policy as Tax ID, ensuring compliance without breaking downstream consumers.

### Transformation rationale for Provider
- `hash` for Tax ID fields preserves length and punctuation (e.g., `##-#######`) enabling joins or validations that depend on shape, while preventing recovery of the original values.
- Deterministic hashing means the same source Tax ID always maps to the same de-identified value across files, aiding cross-file linkage where needed.

### Verifying Provider results
- Compare a sample row before/after for a Tax ID field:
  - Open `Data/Provider/.../*.csv` and the corresponding `De-Identified/Provider/.../*.csv`.
  - Look at `fedid` (or a matched alias). The digits should differ while separators and overall length remain the same.
- If a value appears unchanged, check whether the field is empty or non-numeric; only digit sequences are transformed.

### Member (text/HL7)
- Examples from `Config/Member/rules.json`:
  - `ID`, `MemberID` → `hash`
  - `LastName`, `FirstName`, `MiddleName`, `Suffix` → `pseudonymization` (random but plausible names)
  - `Email`, `HomePhone`, `CellPhone` → `mask`
  - `Gender` → `change` (M↔F, case-aware)
  - `DateOfBirth` → `birthday` (shift 100 days back)
  - Addresses (`ResidentialAddress`, `MailingAddress`) → `pseudonymization` (generate synthetic address)
  - Enrollment and other IDs in named segments → `hash` per sequence in rules

### Claims (text)
- From `Config/Claims/rules.json`:
  - `CLAIM_ID`, `MEM_NBR`, `MEM_ZIP` → `hash`
  - `SVC_PROV_NAME` → `pseudonymization` (synthetic provider name)
  - `MEM_DOB` → `birthday` (shift 100 days back)
  - `MEM_GENDER`, `MEM_STATE`, `MEM_MARKET` → `change` (mapped values)

### Guiding Care (text)
- From `Config/Guiding Care/rules.json` (file-by-file):
  - Most fields `action: none`.
  - Commonly `Member_ID` → `hash`.
  - Header lines skipped where configured (`skiprules`).

## Why You Might “See No Difference” in Output
- Provider flow not executed: Ensure `python main.py` shows “Provider CSV” section, or run `python Provider.py` directly.
- Output location: Check `De-Identified/Provider/...` (same relative paths as input under `Data/Provider`).
- Empty or non-numeric `fedid`: The hasher only replaces numeric substrings; blanks or non-digit-only fields may appear unchanged aside from preserved punctuation.
- Visual similarity: Hashing preserves digit counts and punctuation; values will look similar in shape but digits should differ from the original.

## Extending Provider Rules
- Add more columns to `Config/Provider/rules.json` under `columns` (case-insensitive):
  ```json
  {
    "applyTo": ["*.csv"],
    "caseInsensitive": true,
    "columns": [
      { "name": "fedid", "action": "hash" },
      { "name": "tin",   "action": "hash" },
      { "name": "taxid", "action": "hash" }
    ]
  }
  ```
- Actions available: `hash`, `mask`, `change`, `pseudonymization`, `birthday`, or `none` (see `utils.py`).

## Determinism and Auditability
- `hash` and `birthday` are deterministic given the same input.
- `pseudonymization` (names/addresses) uses randomness and is not deterministic unless you add a random seed.

## Notes
- We intentionally did not modify existing HL7/text code paths to protect previous results.
- Progress indicators print percentages for lengthy files in all modules.
