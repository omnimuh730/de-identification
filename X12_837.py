"""
X12 837 De-identification Module
Parses 837 EDI files and applies de-identification to subscriber/patient
name, address, DOB, gender and member identifiers using rules in Config/X12/837/rules.json.
"""

import os
from typing import List, Tuple, Optional

from utils import (
    load_deid_rules,
    apply_deidentification_action,
    generate_fake_name,
    generate_fake_address,
    mask_data,
)


def detect_delimiters(content: str) -> Tuple[str, str, str]:
    """Detect element, segment, and component separators from ISA if possible.
    Fallback to ('*','~',':').
    """
    # Defaults
    ele = '*'
    seg = '~'
    comp = ':'
    # Try to detect from ISA segment
    # Heuristic: ISA is the first segment, element sep at index 3, segment term is the char before 'GS'
    idx = content.find('ISA')
    if idx != -1 and len(content) > idx + 3:
        try:
            ele = content[idx + 3]
        except Exception:
            pass
        # Segment terminator: char before next 'GS'
        gs = content.find('GS', idx + 1)
        if gs > idx + 1:
            try:
                seg = content[gs - 1]
            except Exception:
                pass
        # Component separator: usually the character right before seg at end of ISA
        # Common default ':' is fine when unknown.
    return ele, seg, comp


def split_segments(content: str, seg_term: str) -> List[str]:
    # Keep empty parts out; trim whitespace
    return [s for s in content.split(seg_term) if s]


def process_file(content: str, rules: dict) -> str:
    ele_sep = rules.get('elementSeparator') or '*'
    seg_term = rules.get('segmentTerminator') or '~'

    # If ISA present, try to auto-detect, but respect configured defaults if present
    auto_ele, auto_seg, _ = detect_delimiters(content)
    if not rules.get('elementSeparator'):
        ele_sep = auto_ele
    if not rules.get('segmentTerminator'):
        seg_term = auto_seg

    name_rules = rules.get('nameSegments', [])
    addr_rules = rules.get('addressSegments', [])
    demo_rules = rules.get('demographicSegments', [])
    id_rules = rules.get('idSegments', [])
    address_context = set(rules.get('addressContextQualifiers', ['IL', 'QC']))

    dmg_cfg = (rules.get('dmg') or {}).get('actions', {})
    dmg_format_idx = int(dmg_cfg.get('formatIndex', 1)) if str(dmg_cfg.get('formatIndex', '')).isdigit() else 1
    dmg_dob_idx = int(dmg_cfg.get('dobIndex', 2)) if str(dmg_cfg.get('dobIndex', '')).isdigit() else 2
    dmg_gender_idx = int(dmg_cfg.get('genderIndex', 3)) if str(dmg_cfg.get('genderIndex', '')).isdigit() else 3
    dmg_format_action = dmg_cfg.get('formatAction', 'none')
    dmg_dob_action = dmg_cfg.get('dobAction', 'birthday')
    dmg_gender_action = dmg_cfg.get('genderAction', 'change')

    pat_cfg = (rules.get('pat') or {}).get('actions', {})
    pat_rel_idx = int(pat_cfg.get('relationshipIndex', 1)) if str(pat_cfg.get('relationshipIndex', '')).isdigit() else 1
    pat_rel_action = pat_cfg.get('relationshipAction', 'none')

    name_targets = {
        r.get('segment'): (r.get('qualifierElement'), set(r.get('qualifiers', [])))
        for r in name_rules if isinstance(r, dict)
    }

    addr_targets = set([r.get('segment') for r in addr_rules if isinstance(r, dict)])
    demo_targets = set([r.get('segment') for r in demo_rules if isinstance(r, dict)])

    # Pre-parse id rules
    ref_hash_quals: Tuple[Optional[int], set] = (None, set())
    nm1_hash_rule = None
    for r in id_rules:
        if r.get('segment') == 'REF':
            ref_hash_quals = (r.get('qualifierElement'), set(r.get('hashQualifiers', [])))
        if r.get('segment') == 'NM1' and 'hashWhen' in r:
            nm1_hash_rule = r['hashWhen']

    segments = split_segments(content, seg_term)

    current_entity = None  # e.g., 'IL' or 'QC' from NM1-02
    current_fake_addr = None  # tuple (street, city, state, zip)

    out_segments: List[str] = []
    for raw_seg in segments:
        seg = raw_seg.strip()
        if not seg:
            continue
        parts = seg.split(ele_sep)
        seg_id = (parts[0] if parts else '').upper()

        # Track entity on NM1
        if seg_id == 'NM1':
            # Reset address cache when hitting a new NM1
            current_fake_addr = None

            # Apply NM1 name rules based on qualifier
            q_idx, q_vals = name_targets.get('NM1', (None, set()))
            qualifier = None
            if isinstance(q_idx, int) and len(parts) > q_idx:
                qualifier = parts[q_idx]
            current_entity = qualifier

            if qualifier and qualifier in q_vals:
                # Pseudonymize name components: NM103=parts[3], NM104=parts[4], NM105=parts[5]
                fake = generate_fake_name()
                if len(parts) > 3 and parts[3]:
                    parts[3] = fake['family']
                if len(parts) > 4 and parts[4]:
                    parts[4] = fake['given']
                if len(parts) > 5 and parts[5]:
                    parts[5] = fake['middle']

            # Hash NM109 when NM108 is 'MI' and qualifier is IL/QC
            if nm1_hash_rule:
                try:
                    q_idx2 = int(nm1_hash_rule.get('qualifierElement', 0))
                    valid_qs = set(nm1_hash_rule.get('qualifiers', []))
                    idq_idx = int(nm1_hash_rule.get('idQualifierElement', 0))
                    idq_val = nm1_hash_rule.get('idQualifier')
                    id_idx = int(nm1_hash_rule.get('idElement', 0))
                except Exception:
                    q_idx2 = None
                    valid_qs = set()
                    idq_idx = None
                    idq_val = None
                    id_idx = None
                if (
                    isinstance(q_idx2, int)
                    and isinstance(idq_idx, int)
                    and isinstance(id_idx, int)
                    and len(parts) > max(q_idx2, idq_idx, id_idx)
                ):
                    if parts[q_idx2] in valid_qs and parts[idq_idx] == idq_val and parts[id_idx]:
                        parts[id_idx] = apply_deidentification_action(parts[id_idx], 'hash')

        elif seg_id in addr_targets:
            # Apply address only for member/patient contexts
            if current_entity in address_context:
                if seg_id == 'N3':
                    # Generate new fake address for this entity context
                    fake_addr = generate_fake_address()
                    bits = fake_addr.split('^')
                    street = bits[0] if len(bits) > 0 else ''
                    # Use N301 as street; keep N302 if present in original, else blank
                    if len(parts) > 1 and street:
                        parts[1] = street
                    if len(parts) > 2 and parts[2]:
                        # Mask N302 to preserve structure while de-identifying
                        parts[2] = mask_data(parts[2])
                    # cache components for N4 to keep consistency
                    city = bits[1] if len(bits) > 1 else ''
                    state = bits[2] if len(bits) > 2 else ''
                    zipc = bits[3] if len(bits) > 3 else ''
                    current_fake_addr = (city, state, zipc)
                elif seg_id == 'N4':
                    city = state = zipc = ''
                    if current_fake_addr:
                        city, state, zipc = current_fake_addr
                    else:
                        fake_addr = generate_fake_address()
                        bits = fake_addr.split('^')
                        city = bits[1] if len(bits) > 1 else ''
                        state = bits[2] if len(bits) > 2 else ''
                        zipc = bits[3] if len(bits) > 3 else ''
                    if len(parts) > 1 and city:
                        parts[1] = city
                    if len(parts) > 2 and state:
                        parts[2] = state
                    if len(parts) > 3 and zipc:
                        parts[3] = apply_deidentification_action(zipc, 'hash')  # hash zip digits

        elif seg_id in demo_targets:
            # DMG for DOB/Gender, only IL/QC contexts
            if current_entity in address_context:
                # DMG01 format, DMG02 DOB, DMG03 Gender per config
                if len(parts) > dmg_format_idx and parts[dmg_format_idx]:
                    parts[dmg_format_idx] = apply_deidentification_action(parts[dmg_format_idx], dmg_format_action)
                if len(parts) > dmg_dob_idx and parts[dmg_dob_idx]:
                    parts[dmg_dob_idx] = apply_deidentification_action(parts[dmg_dob_idx], dmg_dob_action)
                if len(parts) > dmg_gender_idx and parts[dmg_gender_idx]:
                    parts[dmg_gender_idx] = apply_deidentification_action(parts[dmg_gender_idx], dmg_gender_action)

        elif seg_id == 'PAT':
            # Relationship segment; not PII, default action none; configurable
            if (
                isinstance(pat_rel_idx, int)
                and pat_rel_action != 'none'
                and len(parts) > pat_rel_idx
                and parts[pat_rel_idx]
            ):
                parts[pat_rel_idx] = apply_deidentification_action(parts[pat_rel_idx], pat_rel_action)

        elif seg_id == 'REF':
            # Hash REF value when qualifier matches and in IL/QC context
            q_idx, quals = ref_hash_quals
            if current_entity in {'IL', 'QC'} and isinstance(q_idx, int) and len(parts) > q_idx:
                qualifier = parts[q_idx]
                if qualifier in quals and len(parts) > q_idx + 1 and parts[q_idx + 1]:
                    parts[q_idx + 1] = apply_deidentification_action(parts[q_idx + 1], 'hash')

        # Recompose segment
        out_segments.append(ele_sep.join(parts))

    return seg_term.join(out_segments) + seg_term


def process_x12_file(input_file_path: str, output_file_path: str, rules_obj: dict) -> bool:
    print(f"De-identification of {os.path.basename(input_file_path)} started")
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        try:
            with open(input_file_path, 'r', encoding='utf-8', newline='') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(input_file_path, 'r', encoding='latin-1', newline='') as f:
                content = f.read()

        deid = process_file(content, rules_obj)

        with open(output_file_path, 'w', encoding='utf-8', newline='') as out:
            out.write(deid)

        print(f"De-identified X12 837 saved to: {output_file_path}")
        return True
    except Exception as e:
        print(f"Error processing X12 837 file {input_file_path}: {str(e)}")
        return False


def run(input_dir: str, output_dir: str) -> bool:
    print("Starting X12 837 de-identification process...")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    deid_rules_path = os.path.join(script_dir, "Config", "X12", "837", "rules.json")
    if not os.path.exists(deid_rules_path):
        print(f"De-identification rules file not found: {deid_rules_path}")
        return False

    try:
        rules_obj = load_deid_rules(deid_rules_path)
    except Exception as e:
        print(f"Error loading de-identification rules: {str(e)}")
        return False

    os.makedirs(output_dir, exist_ok=True)

    # Collect likely 837 files (common extensions)
    exts = {'.x12', '.X12', '.edi', '.EDI', '.txt', '.TXT', '.837'}
    files: List[str] = []
    for root, _dirs, filenames in os.walk(input_dir):
        for fn in filenames:
            if os.path.splitext(fn)[1] in exts:
                files.append(os.path.join(root, fn))

    total = len(files)
    print(f"{total} X12 files found for de-identification:")
    for fp in files[:25]:  # limit listing
        print(f"  - {os.path.relpath(fp, input_dir)}")
    if total == 0:
        print("No X12 files to process.")
        return False
    print("\nDe-identification starting...")

    success = 0
    for idx, in_path in enumerate(files):
        rel = os.path.relpath(in_path, input_dir)
        out_path = os.path.join(output_dir, rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if process_x12_file(in_path, out_path, rules_obj):
            success += 1
        else:
            print(f"Failed to process: {rel}")
        pct = ((idx + 1) / total) * 100
        print(f"=== {pct:.1f}% === ({idx + 1}/{total} files processed)")

    print("\nX12 837 de-identification completed!")
    print(f"Successfully processed: {success}/{total} files")
    return success == total


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_dir = os.path.join(script_dir, "Data", "X12", "837")
    out_dir = os.path.join(script_dir, "De-Identified", "X12", "837")
    run(in_dir, out_dir)
