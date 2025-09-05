"""
Guiding Care De-identification Module
Processes pipe-delimited text files containing Guiding Care data and applies de-identification rules.
Supports skip rules and field-level actions as defined in rules.json.
"""

import os
from utils import load_deid_rules, apply_deidentification_action

def should_skip_line(line, skiprules):
	"""Check if line should be skipped based on skiprules"""
	for rule in skiprules:
		location = rule.get('location')
		pattern = rule.get('pattern')
		if location == 'start' and line.startswith(pattern):
			return True
	return False

def get_field_action_by_seq(seq, rules):
	"""Get field_name and action for a given sequence number"""
	for rule in rules:
		if rule.get('seq') == seq:
			return rule.get('field_name', ''), rule.get('action', 'none')
	return '', 'none'

def apply_guidingcare_deidentification(line, rules, skiprules):
	"""Apply de-identification rules to a single Guiding Care data line"""
	if not line.strip() or should_skip_line(line, skiprules):
		return line

	fields = line.strip().split('|')
	deidentified_fields = fields.copy()
	for seq, field_value in enumerate(fields):
		field_name, action = get_field_action_by_seq(seq, rules)
		if action != 'none' and field_value:
			deidentified_fields[seq] = apply_deidentification_action(field_value, action)
	return '|'.join(deidentified_fields)

def process_guidingcare_file(input_file_path, output_file_path, rules, skiprules):
	"""Process a single Guiding Care text file"""
	import threading
	import time
	print(f"De-identification of {os.path.basename(input_file_path)} started")
	try:
		os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
		with open(input_file_path, 'r', encoding='utf-8') as infile, \
			 open(output_file_path, 'w', encoding='utf-8') as outfile:
			total_lines = sum(1 for _ in infile)
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
				deidentified_line = apply_guidingcare_deidentification(line.rstrip('\n\r'), rules, skiprules)
				outfile.write(deidentified_line + '\n')
				progress['current'] = i + 1
			t.join()
		print(f"De-identified Guiding Care file saved to: {output_file_path}")
		print(f"Processed {total_lines} lines")
		return True
	except Exception as e:
		print(f"Error processing Guiding Care file {input_file_path}: {str(e)}")
		return False

def run(input_dir, output_dir):
	"""Main function to run Guiding Care de-identification for all configured files"""
	print("Starting Guiding Care de-identification process...")
	print(f"Input directory: {input_dir}")
	print(f"Output directory: {output_dir}")
	script_dir = os.path.dirname(os.path.abspath(__file__))
	deid_rules_path = os.path.join(script_dir, "Config", "Guiding Care", "rules.json")
	if not os.path.exists(deid_rules_path):
		print(f"De-identification rules file not found: {deid_rules_path}")
		return False
	try:
		rules_json = load_deid_rules(deid_rules_path)
		if not rules_json or not isinstance(rules_json, list):
			print("Invalid rules.json format.")
			return False
	except Exception as e:
		print(f"Error loading de-identification rules: {str(e)}")
		return False
	os.makedirs(output_dir, exist_ok=True)
	# Process each file defined in rules.json
	total_count = 0
	success_count = 0
	for rule_set in rules_json:
		fileName = rule_set.get('fileName')
		rules = rule_set.get('rules', [])
		skiprules = rule_set.get('skiprules', [])
		input_file = fileName + ".txt"
		input_file_path = os.path.join(input_dir, input_file)
		output_file_path = os.path.join(output_dir, input_file)
		if os.path.exists(input_file_path):
			print(f"\nProcessing file: {input_file}")
			total_count += 1
			if process_guidingcare_file(input_file_path, output_file_path, rules, skiprules):
				success_count += 1
			else:
				print(f"Failed to process: {input_file}")
		else:
			print(f"File not found, skipping: {input_file}")
	if total_count == 0:
		print("No files to process.")
		return False
	print(f"\nGuiding Care de-identification completed!")
	print(f"Successfully processed: {success_count}/{total_count} files")
	return success_count == total_count

if __name__ == "__main__":
	script_dir = os.path.dirname(os.path.abspath(__file__))
	input_dir = os.path.join(script_dir, "Data", "Guiding Care")
	output_dir = os.path.join(script_dir, "De-Identified", "Guiding Care")
	run(input_dir, output_dir)