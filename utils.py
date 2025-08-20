"""
Utility functions for de-identification operations.
Contains reusable functions for masking, hashing, pseudonymization, and data transformation.
"""

import hashlib
import re
import random
import string
import os
import json

def extract_numbers_and_hash(text, preserve_length=True):
	"""Extract numbers from text, hash them, and replace while preserving format"""
	if not text:
		return text
	
	# Find all numeric sequences (chunks of consecutive digits)
	numbers = re.findall(r'\d+', text)
	if not numbers:
		return text
	
	# Hash each numeric chunk separately and maintain original length
	result = text
	for num_chunk in numbers:
		# Hash the entire chunk as one unit
		hashed = hashlib.sha256(num_chunk.encode()).hexdigest()
		
		# Convert hash to numbers and maintain original chunk length
		hash_numbers = ''.join(filter(str.isdigit, hashed))
		if len(hash_numbers) < len(num_chunk):
			# Extend with more hash digits if needed
			hash_numbers = (hash_numbers * ((len(num_chunk) // len(hash_numbers)) + 1))[:len(num_chunk)]
		else:
			hash_numbers = hash_numbers[:len(num_chunk)]
		
		# Replace the first occurrence of this number chunk
		result = result.replace(num_chunk, hash_numbers, 1)
	
	return result

def mask_data(text):
	"""Apply partial masking to data"""
	if not text or len(text) <= 2:
		return text
	
	# For email-like patterns
	if '@' in text:
		parts = text.split('@')
		if len(parts) == 2:
			local = parts[0]
			domain = parts[1]
			if len(local) > 2:
				masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
			else:
				masked_local = local
			return f"{masked_local}@{domain}"
	
	# For phone numbers with format (xxx)xxx-xxxx
	if re.match(r'^\(\d{3}\)\d{3}-\d{4}', text):
		return f"({text[1:4]}){text[5:8]}-****"
	
	# For dates (YYYYMMDD or YYYY-MM-DD format)
	if re.match(r'^\d{4}[-/]?\d{2}[-/]?\d{2}', text):
		# Keep year, mask month and day
		if '-' in text or '/' in text:
			parts = re.split(r'[-/]', text)
			return f"{parts[0]}-**-**"
		else:
			return text[:4] + "****"
	
	# For general text masking
	if len(text) > 4:
		return text[0] + '*' * (len(text) - 2) + text[-1]
	else:
		return text[0] + '*' * (len(text) - 1)

def change_value(value):
	"""Convert/change values for de-identification"""
	if not value:
		return value
	
	value_lower = value.lower().strip()
	
	# Handle sex/gender
	if value_lower in ['f', 'female']:
		return 'M' if value.isupper() or len(value) == 1 else 'Male'
	elif value_lower in ['m', 'male']:
		return 'F' if value.isupper() or len(value) == 1 else 'Female'
	
	# Handle US states
	state_mapping = {
		'AL': 'CA', 'AK': 'TX', 'AZ': 'FL', 'AR': 'NY', 'CA': 'PA', 'CO': 'IL', 'CT': 'OH', 'DE': 'GA',
		'FL': 'NC', 'GA': 'MI', 'HI': 'NJ', 'ID': 'VA', 'IL': 'WA', 'IN': 'AZ', 'IA': 'MA', 'KS': 'TN',
		'KY': 'IN', 'LA': 'MO', 'ME': 'MD', 'MD': 'WI', 'MA': 'CO', 'MI': 'MN', 'MN': 'SC', 'MS': 'AL',
		'MO': 'LA', 'MT': 'KY', 'NE': 'OR', 'NV': 'OK', 'NH': 'CT', 'NJ': 'IA', 'NM': 'KS', 'NY': 'UT',
		'NC': 'NV', 'ND': 'AR', 'OH': 'MS', 'OK': 'NE', 'OR': 'WV', 'PA': 'ID', 'RI': 'HI', 'SC': 'NH',
		'SD': 'ME', 'TN': 'RI', 'TX': 'MT', 'UT': 'DE', 'VT': 'SD', 'VA': 'ND', 'WA': 'VT', 'WV': 'AK',
		'WI': 'WY', 'WY': 'NM', 'PR': 'VI', 'VI': 'GU', 'GU': 'PR'
	}
	
	# Check if it's a state code
	if value.upper() in state_mapping:
		mapped = state_mapping[value.upper()]
		return mapped if value.isupper() else mapped.lower()
	
	# Handle common market codes or regions
	market_mapping = {
		'PR': 'FL', 'FL': 'TX', 'TX': 'CA', 'CA': 'NY', 'NY': 'IL', 'IL': 'PA', 'PA': 'OH',
		'OH': 'GA', 'GA': 'NC', 'NC': 'MI', 'MI': 'NJ', 'NJ': 'VA', 'VA': 'WA', 'WA': 'AZ',
		'EAST': 'WEST', 'WEST': 'SOUTH', 'SOUTH': 'NORTH', 'NORTH': 'CENTRAL', 'CENTRAL': 'EAST'
	}
	
	if value.upper() in market_mapping:
		mapped = market_mapping[value.upper()]
		return mapped if value.isupper() else mapped.lower()
	
	# For other values, return a generic changed value
	return f"CHG_{hashlib.md5(value.encode()).hexdigest()[:6].upper()}"

def generate_fake_name():
	"""Generate fake name components without external dependencies"""
	first_names = ['JOHN', 'JANE', 'MICHAEL', 'SARAH', 'DAVID', 'EMILY', 'ROBERT', 'JESSICA', 'WILLIAM', 'ASHLEY']
	last_names = ['SMITH', 'JOHNSON', 'WILLIAMS', 'BROWN', 'JONES', 'GARCIA', 'MILLER', 'DAVIS', 'RODRIGUEZ', 'MARTINEZ']
	
	return {
		'family': random.choice(last_names),
		'given': random.choice(first_names),
		'middle': random.choice(first_names)
	}

def generate_fake_address():
	"""Generate fake address components"""
	street_numbers = ['123', '456', '789', '101', '202', '303', '404', '505']
	street_names = ['MAIN ST', 'ELM AVE', 'OAK DRIVE', 'PINE ROAD', 'MAPLE WAY', 'CEDAR LANE', 'PARK BLVD', 'HILL ST']
	cities = ['SPRINGFIELD', 'RIVERSIDE', 'FRANKLIN', 'GEORGETOWN', 'CLINTON', 'MADISON', 'WASHINGTON', 'CHESTER']
	states = ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI']
	
	street_num = random.choice(street_numbers)
	street_name = random.choice(street_names)
	city = random.choice(cities)
	state = random.choice(states)
	zipcode = ''.join([str(random.randint(0, 9)) for _ in range(5)])
	
	return f"{street_num} {street_name}^{city}^{state}^{zipcode}"

def generate_fake_provider_name():
	"""Generate fake provider names"""
	first_names = ['JOHN', 'JANE', 'MICHAEL', 'SARAH', 'DAVID', 'EMILY', 'ROBERT', 'JESSICA', 'WILLIAM', 'ASHLEY']
	last_names = ['SMITH', 'JOHNSON', 'WILLIAMS', 'BROWN', 'JONES', 'GARCIA', 'MILLER', 'DAVIS', 'RODRIGUEZ', 'MARTINEZ']
	
	first = random.choice(first_names)
	last = random.choice(last_names)
	
	return f"{last}, {first}"

def apply_deidentification_action(field_value, action):
	"""Apply the specified de-identification action to a field value"""
	if not field_value or action == 'none':
		return field_value
	
	if action == 'hash':
		return extract_numbers_and_hash(field_value)
	elif action == 'mask':
		return mask_data(field_value)
	elif action == 'change':
		return change_value(field_value)
	elif action == 'pseudonymization':
		# For provider names or general pseudonymization
		if any(indicator in field_value.upper() for indicator in [',', 'DR', 'MD', 'DO']):
			return generate_fake_provider_name()
		else:
			# This will be handled specifically for name and address fields in the main script
			return field_value
	
	return field_value

def process_name_components(name_field, action):
	"""Process name field with caret-delimited components"""
	if not name_field or action == 'none':
		return name_field
	
	if action == 'pseudonymization':
		# Split by caret, generate fake names for each component
		components = name_field.split('^')
		fake_name = generate_fake_name()
		
		# Map components: Family^Given^Middle^...
		new_components = []
		for i, component in enumerate(components):
			if i == 0 and component:  # Family name
				new_components.append(fake_name['family'])
			elif i == 1 and component:  # Given name
				new_components.append(fake_name['given'])
			elif i == 2 and component:  # Middle name
				new_components.append(fake_name['middle'])
			else:
				new_components.append(component)  # Keep other components as is
		
		return '^'.join(new_components)
	else:
		return apply_deidentification_action(name_field, action)

def process_address_components(address_field, action):
	"""Process address field with caret-delimited components"""
	if not address_field or action == 'none':
		return address_field
	
	if action == 'pseudonymization':
		return generate_fake_address()
	else:
		return apply_deidentification_action(address_field, action)

def load_deid_rules(file_path):
	"""Load de-identification rules from JSON file"""
	with open(file_path, 'r') as f:
		return json.load(f)