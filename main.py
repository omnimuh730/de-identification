"""
Main script to run de-identification process.
Simple and scalable entry point for different file types and formats.
"""

import os
import sys

def run_hl7_deidentification(data_path=None, data_deid_path=None, module_name = None):
	if data_path is None or data_deid_path is None:
		print("Data paths not provided, using default paths.")
		return
	
	# Run Data de-identification process
	script_dir = os.path.dirname(os.path.abspath(__file__))
	
	# Import and run Data de-identification
	sys.path.insert(0, script_dir)
	
	try:
		# Import the Data de-identification module
		import importlib.util
		spec = importlib.util.spec_from_file_location("deid_data", 
			os.path.join(script_dir, module_name + ".py"))
		deid_data = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(deid_data)
		
		# Run the de-identification
		return deid_data.run(data_path, data_deid_path)

	except Exception as e:
		print(f"Error running Data de-identification: {str(e)}")
		return False

def run_json_deidentification(input_file_path, output_file_path, module_name):
	if input_file_path is None or output_file_path is None:
		print("Input or output file paths not provided, using default paths.")
		return
	
	try:
		# Import the JSON de-identification module
		import importlib.util
		script_dir = os.path.dirname(os.path.abspath(__file__))
		spec = importlib.util.spec_from_file_location("deid_json", 
			os.path.join(script_dir, module_name + ".py"))
		deid_json = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(deid_json)
		
		# Run the de-identification
		return deid_json.run(input_file_path, output_file_path)

	except Exception as e:
		print(f"Error running JSON de-identification: {str(e)}")
		return False



def run_CareManagement():
	"""Main entry point for Care Management de-identification processes"""
	print("=== De-identification Process ===\n")
 
	"""Highlight in detail what's gonna be processed"""
	print("Processing Care Management files...\n")
	
	# Get current URL and dive into Data/CareManagement
	current_dir = os.path.dirname(os.path.abspath(__file__))
	care_management_dir = os.path.join(current_dir, "Data", "CareManagement")	
	care_management_deid_dir = os.path.join(current_dir, "De-Identified", "CareManagement")

	if not os.path.exists(care_management_dir):
		print(f"Care Management directory does not exist: {care_management_dir}")
		return False
	
	success = True
	
	# Process ADT files if they exist
	adt_path = os.path.join(care_management_dir, "ADT")
	if os.path.exists(adt_path):
		adt_deid_path = os.path.join(care_management_deid_dir, "ADT")
		print("Processing ADT files...")
		adt_success = run_hl7_deidentification(adt_path, adt_deid_path, "ADT")
		if not adt_success:
			success = False
			print("✗ ADT processing failed!")
		else:
			print("✓ ADT processing completed!")
	
	# Process HRA files if they exist
	hra_path = os.path.join(care_management_dir, "HRA")
	if os.path.exists(hra_path):
		hra_deid_path = os.path.join(current_dir, "De-Identified", "HRA")
		print("Processing HRA files...")
		hra_success = run_json_deidentification(hra_path, hra_deid_path, "HRA")
		if not hra_success:
			success = False
			print("✗ HRA processing failed!")
		else:
			print("✓ HRA processing completed!")
	
	if success:
		print("\n✓ Care Management de-identification completed successfully!")
	else:
		print("\n✗ Care Management de-identification process failed!")
	
	return success
def run_GuidingCare():
    
    """Main entry point for de-identification processes"""
    print("=== De-identification Process ===\n")
 
    """Highlight in detail what's gonna be processed"""
    print("Processing Guiding Care files...\n")
    
    # Get current URL and dive into Data/Guiding Care
    current_dir = os.path.dirname(os.path.abspath(__file__))
    care_management_dir = os.path.join(current_dir, "Data", "Guiding Care")	
    care_management_deid_dir = os.path.join(current_dir, "De-Identified", "Guiding Care")

    if not os.path.exists(care_management_dir):
        print(f"Guiding Care directory does not exist: {care_management_dir}")
        return False
    
    success = True
    
    # Process ADT files if they exist
    adt_path = os.path.join(care_management_dir, "ADT")
    if os.path.exists(adt_path):
        adt_deid_path = os.path.join(care_management_deid_dir, "ADT")
        print("Processing ADT files...")
        adt_success = run_hl7_deidentification(adt_path, adt_deid_path, "ADT")
        if not adt_success:
            success = False
            print("✗ ADT processing failed!")
        else:
            print("✓ ADT processing completed!")
    
    # Process Other files
    other_path = os.path.join(care_management_dir, "Other")
    if os.path.exists(other_path):
        other_deid_path = os.path.join(care_management_deid_dir, "Other")
        print("Processing Other files...")
        other_success = run_hl7_deidentification(other_path, other_deid_path, "Other")
        if not other_success:
            success = False
            print("✗ Other files processing failed!")
        else:
            print("✓ Other files processing completed!")
    
    if success:
        print("\n✓ Guiding Care de-identification completed successfully!")
    else:
        print("\n✗ Guiding Care de-identification process failed!")
    
    return success

def run_Claims():
	"""Main entry point for Claims de-identification processes"""
	print("=== De-identification Process ===\n")
 
	"""Highlight in detail what's gonna be processed"""
	print("Processing Claims files...\n")
	
	# Get current directory and dive into Data/Claims
	current_dir = os.path.dirname(os.path.abspath(__file__))
	claims_dir = os.path.join(current_dir, "Data", "Claims")	
	claims_deid_dir = os.path.join(current_dir, "De-Identified", "Claims")

	if not os.path.exists(claims_dir):
		print(f"Claims directory does not exist: {claims_dir}")
		return False
	print("Processing Claims files...")
	success = run_hl7_deidentification(claims_dir, claims_deid_dir, "Claims")

	if success:
		print("\n✓ De-identification completed successfully!")
	else:
		print("\n✗ De-identification process failed!")
	
	return success

def run_Provider():
	"""Main entry point for Provider de-identification processes"""
	print("=== De-identification Process ===\n")
 
	"""Highlight in detail what's gonna be processed"""
	print("Processing Provider files...\n")
	
	# Get current directory and dive into Data/Provider
	current_dir = os.path.dirname(os.path.abspath(__file__))

	# Get Provider path
	provider_path = os.path.join(current_dir, "Data", "Provider")
	provider_deid_path = os.path.join(current_dir, "De-Identified", "Provider")
	
	if not os.path.exists(provider_path):
		print(f"Provider directory does not exist: {provider_path}")
		return False
	print("Processing Provider files...")
	success = run_hl7_deidentification(provider_path, provider_deid_path, "Provider")

	if success:
		print("\n✓ De-identification completed successfully!")
	else:
		print("\n✗ De-identification process failed!")
	
	return success

def run_Member():
    """Main entry point for Member de-identification processes"""
    print("=== De-identification Process ===\n")

    """Highlight in detail what's gonna be processed"""
    print("Processing Member files...\n")

    # Get current directory and dive into Data/Member
    current_dir = os.path.dirname(os.path.abspath(__file__))
    member_dir = os.path.join(current_dir, "Data", "Member")
    member_deid_dir = os.path.join(current_dir, "De-Identified", "Member")

    if not os.path.exists(member_dir):
        print(f"Member directory does not exist: {member_dir}")
        return False
    print("Processing Member files...")
    success = run_hl7_deidentification(member_dir, member_deid_dir, "Member")

    if success:
        print("\n✓ De-identification completed successfully!")
    else:
        print("\n✗ De-identification process failed!")
    
    return success

def main():
	
	run_CareManagement()
 
	run_GuidingCare()

	run_Claims()

	run_Provider()
	
	run_Member()

	# Future expansion point for other file types:
	# - CCD files
	# - Other healthcare data formats

if __name__ == "__main__":
	main()
