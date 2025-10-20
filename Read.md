# 837 X12 De-identification Playbook

This guide explains how member and patient PHI is de-identified in ANSI X12 837 professional dental (`837D`) claim files. It is written so validators can reproduce the run, understand every transformation, and confirm that outputs remain structurally valid for downstream systems.

## Scope and Objectives
- **Inputs**: Raw 837 files placed under `Data/X12/837`. The sample file in this repository (`Data/X12/837/TSA_0709/837D_TSA_2025070901_660707485_905775641_20250710005041.x12`) uses the standard element separator `*` and segment terminator `~`.
- **Outputs**: De-identified copies written to `De-Identified/X12/837`, preserving the relative folder structure of the inputs.
- **Targets**: Subscriber (loop 2000B/2010BA) and patient (loop 2000C/2010CA) names, identifiers, addresses, dates of birth, genders, and reference IDs. Claim-level financial data remains untouched.

Other feeds (Member, Claims, Guiding Care, Provider CSV) exist in the repo but fall outside this document.

## Files to Know
- `X12_837.py` – processing script; can run standalone or via `main.py`.
- `Config/X12/837/rules.json` – rule configuration that controls which segments/elements are modified and which action to apply.
- `Config/X12/837/837_Layout.txt` – mapping reference showing loop/segment/element positions for member and patient data.
- `Config/X12/837/837_doc.txt` – business requirements that motivated the extraction and de-identification scope.
- `utils.py` – shared library containing the hash, mask, pseudonymization, and date-shift helpers.

Keep these files in sync when promoting updates. Validators should review `rules.json` and this playbook together.

## Running the Processor
1. Open a terminal at the repository root (`c:\Users\jj751487\Downloads\FS`).
2. Execute:
   ```
   python X12_837.py
   ```
   The script will:
   - Load `Config/X12/837/rules.json`.
   - Discover all files with extensions `.x12`, `.edi`, `.txt`, or `.837` under `Data/X12/837`.
   - Write their de-identified counterparts into `De-Identified/X12/837`.
3. Watch the console output. For each file you should see `De-identification of <file> started` and `De-identified X12 837 saved to: ...` followed by a progress banner (`=== 60.0% ===`).
4. When the run completes, verify that the success summary shows every file processed (e.g., `Successfully processed: 1/1 files`).

> Validation tip: remove or archive prior contents of `De-Identified/X12/837` before each run so you only review fresh outputs.

## What the Rules Do
The rule file contains these key sections (element indexes are zero-based inside the script, one-based in X12 documentation):

| Rule Group | Applicable Segment(s) | Context | Elements affected | Action | Result |
|------------|-----------------------|---------|-------------------|--------|--------|
| `nameSegments` | `NM1` | When `NM102` equals `IL` (subscriber) or `QC` (patient) | `NM103` (last), `NM104` (first), `NM105` (middle) | `pseudonymization` via `generate_fake_name()` | Replaces with uppercase synthetic names. |
| `addressSegments` | `N3`, `N4` | Follows a qualifying `NM1` | `N301` (street), `N302` (optional line 2), `N401-403` (city/state/ZIP) | `pseudonymization` + `mask` + `hash` | Provides a synthetic street, random city/state, and hashes ZIP digits while keeping format. |
| `demographicSegments` | `DMG` | Same subscriber/patient context | `DMG02` (DOB) and `DMG03` (gender) | `birthday`, `change` | DOB shifted back 100 days; gender flipped (`M↔F`) with casing preserved. |
| `idSegments` | `REF`, `NM1` | `REF` with qualifiers `SY` or `MI`; `NM1` when `NM108`=`MI` | Value component or `NM109` | `hash` | Digit sequences replaced with deterministic hashed digits; punctuation retained. |
| `pat.actions` | `PAT` | Patient loop | `PAT01` | `none` (configurable) | Relationship codes are left untouched in this release. |

Actions are implemented in `utils.py`. Notable behaviors:
- `hash` (`extract_numbers_and_hash`) only changes numeric sequences and keeps length/format, so `123-45-6789` could become `742-93-1056`.
- `birthday` subtracts 100 days from valid `YYYYMMDD` dates.
- `pseudonymization` for names/addresses uses random selections; outputs are not deterministic run-to-run.

## Processing Flow Overview
1. **Delimiter detection** – the script reads the `ISA` segment and auto-detects the element separator and segment terminator. If the rules file specifies explicit separators they override auto-detection.
2. **Segment iteration** – each segment is split; when an `NM1` segment matches the configured qualifiers the script records the context (`IL` or `QC`).
3. **Name replacement** – qualifying `NM1` segments receive new synthetic last/first/middle names.
4. **Address rewrite** – the following `N3` segment gets a generated street; `N4` reuses the same fake city/state and hashes the ZIP digits.
5. **Demographics** – in the same context, `DMG02` is shifted back 100 days and `DMG03` is flipped. `DMG01` (format indicator) is left unchanged.
6. **Identifiers** – `REF` segments with qualifiers in the hash list and `NM109` (when the ID qualifier is `MI`) are hashed. This produces consistent pseudo-identifiers across files.
7. **Output assembly** – segments are rejoined using the detected separators, and the original terminator is appended after every segment to preserve EDI compliance.

## Validator Checklist
Use this list before, during, and after execution.

- **Pre-run checks**
  - Confirm the correct configuration is in place: compare the checksum or timestamp of `Config/X12/837/rules.json` against the approved version.
  - Verify input files begin with an `ISA` segment. Reject malformed files prior to processing.
  - Clear or archive prior outputs from `De-Identified/X12/837`.
- **During execution**
  - Monitor standard output for runtime errors. The script prints stack traces if a file fails.
  - Ensure the progress indicator advances through all files discovered.
- **Post-run verification**
  - The count of files in `De-Identified/X12/837` should equal the count in `Data/X12/837` (sub-folders included). If not, review the log for failures.
  - Open a sample output file and confirm segment terminators (`~`) and element separators (`*`) match the source.
  - Confirm there are no extra or missing `CLM` segments by performing a simple `CLM` count comparison between input and output.

## Field-Level Validation Steps
Reference `Config/X12/837/837_Layout.txt` for loop/segment/element positions.

### Subscriber loop 2000B / 2010BA
- **Names** (`NM1*IL`):
  - `NM103`–`NM105` must contain uppercase synthetic values unrelated to the original names.
  - `NM109` (member identifier) should change while preserving separators and length.
- **Address** (`N3` & `N4`):
  - `N301` should show a synthetic street (number + street name). Optional `N302` is masked if present.
  - `N401`/`N402` should reflect new city/state values; `N403` must show different digits but keep ZIP-length.
- **Demographics** (`DMG*D8`):
  - `DMG02` equals original DOB minus 100 days.
  - `DMG03` flips gender (`M` to `F`, `F` to `M`).

### Patient loop 2000C / 2010CA
- Apply the same checks for `NM1*QC`, `DMG`, `N3`, and `N4`. Note that this loop is optional; if absent the subscriber loop represents both member and patient.

### Reference identifiers (`REF`)
- For `REF*SY` and `REF*MI` segments within subscriber or patient contexts, confirm the qualifier stays the same and the value element is hashed (digits differ, punctuation intact).
- Non-numeric values may remain unchanged because the hash routine only replaces digits; document any such cases for sign-off.

### Segments intentionally untouched
- `PAT*` relationship codes (e.g., `PAT*18~`) currently remain unchanged per business guidance.
- Claim lines, provider data, financial amounts, and trailer segments are left exactly as received. If diffs are observed here, treat them as red flags.

## Troubleshooting
- **No files processed** – confirm input extensions are supported (`.x12`, `.edi`, `.txt`, `.837`) and that they reside under `Data/X12/837`.
- **Delimiters change unexpectedly** – inspect the source `ISA` segment. Custom terminators must appear in the positions the script reads; otherwise the fallback (`*`, `~`) is used.
- **Name or address unchanged** – ensure the preceding `NM1` qualifier is `IL` or `QC`. If additional qualifiers need coverage, add them to `addressContextQualifiers` in `rules.json`.
- **DOB unchanged** – verify the original format is `YYYYMMDD`. The date shift only runs on valid 8-digit strings.
- **Hashed ID looks identical** – if the value contained no digits, hashing has no effect. Document and confirm with stakeholders whether alpha-only IDs need masking.

## Extending the Rules
- Modify `Config/X12/837/rules.json` to add new qualifiers, segments, or actions. Example: to mask `PAT01`, set `"relationshipAction": "mask"`.
- When new actions are introduced, update `utils.py` if needed and provide validators with revised instructions.
- Always rerun your validation suite (file counts, field spot checks, DOB offsets) after any configuration change.

Following this playbook ensures each validator can reproduce the run, trace every transformation back to `rules.json`, and confirm that subscriber and patient PHI is fully de-identified while the EDI structure stays intact.
