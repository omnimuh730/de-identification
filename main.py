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
	run_Member()

	# Future expansion point for other file types:
	# - CCD files
	# - Other healthcare data formats

if __name__ == "__main__":
	main()
