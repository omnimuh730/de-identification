"""
Provider CSV De-identification Module
Processes CSV files and applies de-identification based on column names.
Focus: Hash Tax ID columns (e.g., fedid) per rules in Config/Provider/rules.json.
"""

import os
import fnmatch
import csv
import re
from utils import load_deid_rules, apply_deidentification_action


def _normalize(name: str) -> str:
    return (name or "").strip().lower()


def _build_column_action_map(header, rules_obj):
    """Return a dict: column_index -> action, based on header names and rules.

    Supports:
      - Exact name matching ("name")
      - Pattern matching with { match: { mode: exact|icontains|regex, value: <str> } }
    """
    if not isinstance(rules_obj, dict):
        return {}

    case_insensitive = bool(rules_obj.get("caseInsensitive", True))

    columns_spec = rules_obj.get("columns", [])
    name_to_action = {}
    matchers = []  # list of tuples (callable(header_name) -> bool, action)

    if isinstance(columns_spec, dict):
        # { "fedid": "hash", ... }
        for k, v in columns_spec.items():
            name_to_action[_normalize(k) if case_insensitive else k] = v
    elif isinstance(columns_spec, list):
        for c in columns_spec:
            if not isinstance(c, dict):
                continue
            ac = c.get("action", "none")
            nm = c.get("name")
            if nm:
                name_to_action[_normalize(nm) if case_insensitive else nm] = ac
                continue
            m = c.get("match")
            if isinstance(m, dict):
                mode = (m.get("mode") or "exact").lower()
                value = m.get("value")
                if not isinstance(value, str):
                    continue
                if case_insensitive and mode != "regex":
                    value_ci = value.lower()
                else:
                    value_ci = value
                if mode == "exact":
                    def mk_exact(val):
                        return lambda s: (_normalize(s) == _normalize(val)) if case_insensitive else (s == val)
                    matchers.append((mk_exact(value), ac))
                elif mode == "icontains":
                    def mk_icontains(val):
                        return lambda s: (val.lower() in _normalize(s))
                    matchers.append((mk_icontains(value), ac))
                elif mode == "regex":
                    try:
                        flags = re.IGNORECASE if case_insensitive else 0
                        rx = re.compile(value, flags)
                        matchers.append((lambda s, _rx=rx: bool(_rx.search(s or "")), ac))
                    except re.error:
                        continue

    col_actions = {}
    for idx, col_name in enumerate(header):
        key = _normalize(col_name) if case_insensitive else col_name
        # exact name first
        if key in name_to_action:
            col_actions[idx] = name_to_action[key]
            continue
        # then patterns
        for predicate, action in matchers:
            try:
                if predicate(col_name):
                    col_actions[idx] = action
                    break
            except Exception:
                continue
    return col_actions


def _matches_any(name: str, patterns):
    if not patterns:
        return False
    for pat in patterns:
        if fnmatch.fnmatch(name, pat):
            return True
    return False


def process_provider_csv_file(input_file_path, output_file_path, rules_obj):
    """Process a single CSV file using column-name-based rules."""
    import threading
    import time
    print(f"De-identification of {os.path.basename(input_file_path)} started")
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        # Count total lines (excluding header) for progress
        try:
            with open(input_file_path, 'r', encoding='utf-8', newline='') as fcount:
                total_lines = sum(1 for _ in fcount)
        except UnicodeDecodeError:
            with open(input_file_path, 'r', encoding='latin-1', newline='') as fcount:
                total_lines = sum(1 for _ in fcount)
        total_data_lines = max(total_lines - 1, 0)

        progress = {'current': 0, 'total': total_data_lines}

        def progress_printer():
            last_percent = -1
            while progress['current'] < progress['total']:
                if progress['total'] == 0:
                    percent = 100
                else:
                    percent = int((progress['current'] / progress['total']) * 100)
                if percent != last_percent:
                    print(f"\r{percent}%", end='', flush=True)
                    last_percent = percent
                time.sleep(0.05)
            print(f"\r100%", flush=True)

        t = threading.Thread(target=progress_printer)
        t.start()

        # Read + write CSV with csv module
        # Use UTF-8, fallback to latin-1 if needed
        try:
            infile = open(input_file_path, 'r', encoding='utf-8', newline='')
        except UnicodeDecodeError:
            infile = open(input_file_path, 'r', encoding='latin-1', newline='')

        with infile as inf, open(output_file_path, 'w', encoding='utf-8', newline='') as outf:
            reader = csv.reader(inf)
            writer = csv.writer(outf)

            # Header row
            try:
                header = next(reader)
            except StopIteration:
                # Empty file, just write nothing
                t.join()
                return True

            writer.writerow(header)
            col_actions = _build_column_action_map(header, rules_obj)

            # Process rows
            for row in reader:
                if not row:
                    writer.writerow(row)
                    continue
                new_row = list(row)
                for idx, action in col_actions.items():
                    if 0 <= idx < len(new_row) and new_row[idx]:
                        new_row[idx] = apply_deidentification_action(new_row[idx], action)
                writer.writerow(new_row)
                progress['current'] += 1

        t.join()
        print(f"De-identified Provider CSV saved to: {output_file_path}")
        print(f"Processed {progress['total']} rows")
        return True
    except Exception as e:
        print(f"Error processing Provider CSV {input_file_path}: {str(e)}")
        return False


def _find_override_rules(script_dir, rel_path):
    """Return a per-file rules.json path if present.

    Looks for Config/Provider/<rel_dir>/<base>.json next to the file's
    relative directory under Data/Provider.
    """
    rel_dir = os.path.dirname(rel_path)
    base = os.path.splitext(os.path.basename(rel_path))[0]
    # File-specific rules named after the CSV (case-insensitive on Windows)
    candidate = os.path.join(
        script_dir, "Config", "Provider", rel_dir, f"{base}.json"
    )
    if os.path.exists(candidate):
        return candidate
    # Also allow lower-cased filename for portability
    candidate_lower = os.path.join(
        script_dir, "Config", "Provider", rel_dir, f"{base.lower()}.json"
    )
    if os.path.exists(candidate_lower):
        return candidate_lower
    return None


def run(input_dir, output_dir):
    """Main function to run Provider CSV de-identification recursively under input_dir.

    Supports global rules in Config/Provider/rules.json and optional per-file
    overrides co-located under Config/Provider/<subdir>/<filename>.json.
    """
    print("Starting Provider CSV de-identification process...")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    deid_rules_path = os.path.join(script_dir, "Config", "Provider", "rules.json")
    if not os.path.exists(deid_rules_path):
        print(f"De-identification rules file not found: {deid_rules_path}")
        return False

    try:
        rules_obj = load_deid_rules(deid_rules_path)
    except Exception as e:
        print(f"Error loading de-identification rules: {str(e)}")
        return False

    os.makedirs(output_dir, exist_ok=True)

    patterns = []
    if isinstance(rules_obj, dict):
        pats = rules_obj.get("applyTo")
        if isinstance(pats, list):
            patterns = pats

    # Collect CSV files recursively
    files = []
    for root, _dirs, filenames in os.walk(input_dir):
        for fn in filenames:
            if fn.lower().endswith('.csv'):
                if patterns:
                    if _matches_any(fn, patterns):
                        files.append(os.path.join(root, fn))
                else:
                    files.append(os.path.join(root, fn))

    total_count = len(files)
    print(f"{total_count} CSV files found for de-identification:")
    for fp in files:
        print(f"  - {os.path.relpath(fp, input_dir)}")
    if total_count == 0:
        print("No CSV files to process.")
        return False
    print("\nDe-identification starting...")

    success_count = 0
    for idx, in_path in enumerate(files):
        rel = os.path.relpath(in_path, input_dir)
        out_path = os.path.join(output_dir, rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # Choose effective rules: per-file override if present, else global
        effective_rules = rules_obj
        try:
            override_path = _find_override_rules(script_dir, rel)
            if override_path:
                effective_rules = load_deid_rules(override_path)
                print(f"Using override rules: {os.path.relpath(override_path, script_dir)}")
        except Exception as ex:
            print(f"Warning: failed to load override rules for {rel}: {ex}")

        if process_provider_csv_file(in_path, out_path, effective_rules):
            success_count += 1
        else:
            print(f"Failed to process: {rel}")
        percent = ((idx + 1) / total_count) * 100
        print(f"=== {percent:.1f}% === ({idx + 1}/{total_count} files processed)")

    print("\nProvider CSV de-identification completed!")
    print(f"Successfully processed: {success_count}/{total_count} files")
    return success_count == total_count


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, "Data", "Provider")
    output_dir = os.path.join(script_dir, "De-Identified", "Provider")
    run(input_dir, output_dir)
