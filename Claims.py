"""
Claims De-identification Module
Processes pipe-delimited text files containing Claims data and applies de-identification rules.
Handles multiple segment types including Header, named segments, and generic '*' segments.
"""

import os
import shutil
from utils import load_deid_rules, apply_deidentification_action, process_name_components, process_address_components

def identify_segment_type(line, deid_rules):
    """Identify the segment type of a line based on content and rules"""
    if not line.strip():
        return None, []
    
    fields = line.strip().split('|')
    
    # Simple check for header: if the first field is 'CLAIM_ID', it's a header
    if fields and fields[0] == 'CLAIM_ID':
        return 'Header', fields
    
    # Otherwise, assume it's a CLAIMS data row
    return 'CLAIMS', fields

def get_field_action_by_seg_and_seq(segment_type, field_seq, deid_rules):
    """Get the de-identification action for a field based on segment type and sequence"""
    for rule in deid_rules:
        if rule.get('seg') == segment_type and rule.get('seq') == field_seq:
            return rule.get('field_name', ''), rule.get('action', 'none')
    return '', 'none'

def get_field_action_by_name(field_name, segment_type, deid_rules):
    """Get the de-identification action for a field by name and segment"""
    for rule in deid_rules:
        if rule.get('seg') == segment_type and rule.get('field_name') == field_name:
            return rule.get('action', 'none')
    return 'none'

def apply_claims_deidentification(line, deid_rules):
    """Apply de-identification rules to a single Claims data line"""
    if not line.strip():
        return line
    
    segment_type, fields = identify_segment_type(line, deid_rules)
    if not segment_type:
        return line
    
    deidentified_fields = fields.copy()
    # Apply de-identification based on field sequence and segment type
    for field_seq, field_value in enumerate(fields):
        if not field_value:
            continue
        field_name, action = get_field_action_by_seg_and_seq(segment_type, field_seq, deid_rules)
        if action != 'none':
            original_value = field_value
            if 'Name' in field_name and action == 'pseudonymization':
                deidentified_value = apply_claims_name_pseudonymization(field_value)
            elif 'Address' in field_name and action == 'pseudonymization':
                deidentified_value = apply_claims_address_pseudonymization(field_value)
            else:
                deidentified_value = apply_deidentification_action(original_value, action)
            deidentified_fields[field_seq] = deidentified_value
    return '|'.join(deidentified_fields)

def apply_claims_name_pseudonymization(name_field):
    """Apply name pseudonymization for Claims format (space-separated names)"""
    if not name_field:
        return name_field
    
    from utils import generate_fake_name
    
    name_parts = name_field.split()
    fake_names = []
    
    for _ in name_parts:
        fake_name = generate_fake_name()
        fake_names.append(fake_name['given'])
    
    return ' '.join(fake_names)

def apply_claims_address_pseudonymization(address_field):
    """Apply address pseudonymization for Claims format"""
    if not address_field:
        return address_field
    
    from utils import generate_fake_address
    
    fake_address = generate_fake_address()
    street_part = fake_address.split('^')[0] if '^' in fake_address else fake_address
    
    return street_part

def process_claims_file(input_file_path, output_file_path, deid_rules):
    """Process a single Claims text file"""
    import threading
    import sys
    import time
    print(f"De-identification of {os.path.basename(input_file_path)} started")
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        with open(input_file_path, 'r', encoding='utf-8') as infile, \
             open(output_file_path, 'w', encoding='utf-8') as outfile:
            total_lines = 0
            for _ in infile:
                total_lines += 1
            infile.seek(0)

            progress = {'current': 0}
            def progress_printer():
                last_percent = -1
                while progress['current'] < total_lines:
                    percent = int((progress['current'] / total_lines) * 100)
                    if percent != last_percent:
                        print(f"\r{percent}%", end='', flush=True)
                        last_percent = percent
                    time.sleep(0.05)
                print(f"\r100%", flush=True)

            t = threading.Thread(target=progress_printer)
            t.start()

            for i, line in enumerate(infile):
                deidentified_line = apply_claims_deidentification(line.rstrip('\n\r'), deid_rules)
                outfile.write(deidentified_line + '\n')
                progress['current'] = i + 1

            t.join()

        print(f"De-identified Claims file saved to: {output_file_path}")
        print(f"Processed {total_lines} lines")
        return True
    except Exception as e:
        print(f"Error processing Claims file {input_file_path}: {str(e)}")
        return False

def run(input_dir, output_dir):
    """Main function to run Claims de-identification"""
    print("Starting Claims de-identification process...")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    deid_rules_path = os.path.join(script_dir, "Config", "Claims", "rules.json")
    if not os.path.exists(deid_rules_path):
        print(f"De-identification rules file not found: {deid_rules_path}")
        return False
    try:
        deid_rules = load_deid_rules(deid_rules_path)
        print(f"Loaded {len(deid_rules)} de-identification rules")
        segments = set(rule.get('seg') for rule in deid_rules)
        print(f"Segment types in rules: {segments}")
    except Exception as e:
        print(f"Error loading de-identification rules: {str(e)}")
        return False
    
    os.makedirs(output_dir, exist_ok=True)
    
    file_list = [f for f in os.listdir(input_dir) if f.endswith(('.txt', '.hl7')) and f != 'deid_rules.json']
    total_count = len(file_list)
    print(f"{total_count} files found for de-identification:")
    for fname in file_list:
        print(f"  - {fname}")
    if total_count == 0:
        print("No files to process.")
        return False
    print("\nDe-identification starting...")

    success_count = 0
    for idx, filename in enumerate(file_list):
        input_file_path = os.path.join(input_dir, filename)
        output_file_path = os.path.join(output_dir, filename)
        if process_claims_file(input_file_path, output_file_path, deid_rules):
            success_count += 1
        else:
            print(f"Failed to process: {filename}")
        percent = ((idx + 1) / total_count) * 100
        print(f"=== {percent:.1f}% === ({idx + 1}/{total_count} files processed)")

    print(f"\nClaims de-identification completed!")
    print(f"Successfully processed: {success_count}/{total_count} files")
    return success_count == total_count

if __name__ == "__main__":
    import sys
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, "Data", "Claims")
    output_dir = os.path.join(script_dir, "De-Identified", "Claims")
    
    run(input_dir, output_dir)
