"""
Member De-identification Module
Processes pipe-delimited text files containing Member data and applies de-identification rules.
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
    
    # Check if it's a Header segment (has pattern field ending with .txt or .hl7)
    header_rules = [rule for rule in deid_rules if rule.get('seg') == 'Header']
    for rule in header_rules:
        if 'pattern' in rule:
            field_seq = rule.get('seq', 0)
            if field_seq < len(fields):
                field_value = fields[field_seq]
                patterns = rule.get('pattern', [])
                for pattern in patterns:
                    if pattern == '*.txt' and field_value.endswith('.txt'):
                        return 'Header', fields
                    elif pattern == '*.hl7' and field_value.endswith('.hl7'):
                        return 'Header', fields
    
    # Check if it's a named segment (first field matches a known segment name)
    known_segments = set()
    for rule in deid_rules:
        seg = rule.get('seg')
        if seg and seg not in ['Header', '*']:
            known_segments.add(seg)
    
    if fields and fields[0] in known_segments:
        return fields[0], fields
    
    # Check if it's a Trailer segment (look for specific patterns)
    if len(fields) >= 2 and any('trailer' in rule.get('seg', '').lower() for rule in deid_rules):
        # Simple heuristic: if it looks like a trailer (short line with dates)
        if len(fields) <= 3 and all(field.isdigit() or not field for field in fields):
            return 'Trailer', fields
    
    # Default to '*' segment (generic member data)
    return '*', fields

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

def apply_member_deidentification(line, deid_rules):
    """Apply de-identification rules to a single Member data line"""
    if not line.strip():
        return line
    
    segment_type, fields = identify_segment_type(line, deid_rules)
    if not segment_type:
        return line
    
    print(f"Processing {segment_type} segment with {len(fields)} fields")
    
    deidentified_fields = fields.copy()
    
    # Apply de-identification based on field sequence and segment type
    for field_seq, field_value in enumerate(fields):
        if not field_value:  # Skip empty fields
            continue
            
        field_name, action = get_field_action_by_seg_and_seq(segment_type, field_seq, deid_rules)
        
        if action != 'none':
            original_value = field_value
            
            # Special handling for different field types
            if 'Name' in field_name and action == 'pseudonymization':
                # Handle name fields with space-separated multiple names
                deidentified_value = apply_member_name_pseudonymization(field_value)
            elif 'Address' in field_name and action == 'pseudonymization':
                # Handle address fields
                deidentified_value = apply_member_address_pseudonymization(field_value)
            else:
                # Apply standard de-identification
                deidentified_value = apply_deidentification_action(original_value, action)
            
            deidentified_fields[field_seq] = deidentified_value
            
            if field_seq < 5:  # Show progress for first few fields only
                print(f"Applied {action} to field {field_seq} ({field_name}): {original_value} -> {deidentified_value}")
    
    return '|'.join(deidentified_fields)

def apply_member_name_pseudonymization(name_field):
    """Apply name pseudonymization for Member format (space-separated names)"""
    if not name_field:
        return name_field
    
    from utils import generate_fake_name
    
    # Split by spaces to handle multiple names in one field
    name_parts = name_field.split()
    fake_names = []
    
    for _ in name_parts:
        fake_name = generate_fake_name()
        fake_names.append(fake_name['given'])  # Use given names for all parts
    
    return ' '.join(fake_names)

def apply_member_address_pseudonymization(address_field):
    """Apply address pseudonymization for Member format"""
    if not address_field:
        return address_field
    
    from utils import generate_fake_address
    
    # Generate fake address and extract the street part
    fake_address = generate_fake_address()
    # Extract just the street part (before the first ^)
    street_part = fake_address.split('^')[0] if '^' in fake_address else fake_address
    
    return street_part

def process_member_file(input_file_path, output_file_path, deid_rules):
    """Process a single Member text file"""
    print(f"Processing Member file: {input_file_path}")
    
    try:
        with open(input_file_path, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()
        
        deidentified_lines = []
        for i, line in enumerate(lines):
            deidentified_line = apply_member_deidentification(line.rstrip('\n\r'), deid_rules)
            deidentified_lines.append(deidentified_line)
            
            if i < 10:  # Show progress for first 10 lines
                print(f"Processed line {i + 1}")
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        # Write de-identified data
        with open(output_file_path, 'w', encoding='utf-8') as outfile:
            for line in deidentified_lines:
                outfile.write(line + '\n')
        
        print(f"De-identified Member file saved to: {output_file_path}")
        print(f"Processed {len(deidentified_lines)} lines")
        return True
        
    except Exception as e:
        print(f"Error processing Member file {input_file_path}: {str(e)}")
        return False

def run(input_dir, output_dir):
    """Main function to run Member de-identification"""
    print("Starting Member de-identification process...")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    
    # Load de-identification rules
    deid_rules_path = os.path.join(input_dir, "deid_rules.json")
    if not os.path.exists(deid_rules_path):
        print(f"De-identification rules file not found: {deid_rules_path}")
        return False
    
    try:
        deid_rules = load_deid_rules(deid_rules_path)
        print(f"Loaded {len(deid_rules)} de-identification rules")
        
        # Debug: Show segment types found in rules
        segments = set(rule.get('seg') for rule in deid_rules)
        print(f"Segment types in rules: {segments}")
        
    except Exception as e:
        print(f"Error loading de-identification rules: {str(e)}")
        return False
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Note: We don't copy the rules file for Member data as it only processes .txt and .hl7 files
    
    # Process all text and HL7 files in input directory
    success_count = 0
    total_count = 0
    
    for filename in os.listdir(input_dir):
        if filename.endswith(('.txt', '.hl7')) and filename != 'deid_rules.json':
            input_file_path = os.path.join(input_dir, filename)
            output_file_path = os.path.join(output_dir, filename)
            
            total_count += 1
            if process_member_file(input_file_path, output_file_path, deid_rules):
                success_count += 1
            else:
                print(f"Failed to process: {filename}")
    
    print(f"\nMember de-identification completed!")
    print(f"Successfully processed: {success_count}/{total_count} files")
    
    return success_count == total_count

if __name__ == "__main__":
    # Test with default paths
    import sys
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, "Data", "Member")
    output_dir = os.path.join(script_dir, "De-Identified", "Member")
    
    run(input_dir, output_dir)
