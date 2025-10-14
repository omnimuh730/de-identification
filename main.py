"""
Main script to run de-identification process.
Simple and scalable entry point for different file types and formats.
"""

import os
import sys


def run_hl7_deidentification(data_path=None, data_deid_path=None, module_name=None):
    if data_path is None or data_deid_path is None:
        print("Data paths not provided, using default paths.")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "deid_data", os.path.join(script_dir, module_name + ".py")
        )
        deid_data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(deid_data)
        return deid_data.run(data_path, data_deid_path)
    except Exception as e:
        print(f"Error running Data de-identification: {str(e)}")
        return False


def run_Member():
    print("=== De-identification Process ===\n")
    print("Processing Member files...\n")
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


def run_Claims():
    print("=== De-identification Process (Claims) ===\n")
    print("Processing Claims files...\n")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    claims_dir = os.path.join(current_dir, "Data", "Claims")
    claims_deid_dir = os.path.join(current_dir, "De-Identified", "Claims")
    if not os.path.exists(claims_dir):
        print(f"Claims directory does not exist: {claims_dir}")
        return False
    print("Processing Claims files...")
    success = run_hl7_deidentification(claims_dir, claims_deid_dir, "Claims")
    if success:
        print("\n✓ Claims de-identification completed successfully!")
    else:
        print("\n✗ Claims de-identification process failed!")
    return success


def run_GuidingCare():
    print("=== De-identification Process (Guiding Care) ===\n")
    print("Processing Guiding Care files...\n")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    gc_dir = os.path.join(current_dir, "Data", "Guiding Care")
    gc_deid_dir = os.path.join(current_dir, "De-Identified", "Guiding Care")
    if not os.path.exists(gc_dir):
        print(f"Guiding Care directory does not exist: {gc_dir}")
        return False
    print("Processing Guiding Care files...")
    from GuidingCare import run as run_guidingcare
    success = run_guidingcare(gc_dir, gc_deid_dir)
    if success:
        print("\n✓ Guiding Care de-identification completed successfully!")
    else:
        print("\n✗ Guiding Care de-identification process failed!")
    return success


def run_Provider():
    print("=== De-identification Process (Provider CSV) ===\n")
    print("Processing Provider CSV files...\n")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    provider_dir = os.path.join(current_dir, "Data", "Provider")
    provider_deid_dir = os.path.join(current_dir, "De-Identified", "Provider")
    if not os.path.exists(provider_dir):
        print(f"Provider directory does not exist: {provider_dir}")
        return False
    print("Processing Provider CSV files...")
    success = run_hl7_deidentification(provider_dir, provider_deid_dir, "Provider")
    if success:
        print("\n✓ Provider CSV de-identification completed successfully!")
    else:
        print("\n✗ Provider CSV de-identification process failed!")
    return success


def run_X12_837():
    print("=== De-identification Process (X12 837) ===\n")
    print("Processing X12/837 files...\n")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    x12_dir = os.path.join(current_dir, "Data", "X12", "837")
    x12_deid_dir = os.path.join(current_dir, "De-Identified", "X12", "837")
    if not os.path.exists(x12_dir):
        print(f"X12/837 directory does not exist: {x12_dir}")
        return False
    print("Processing X12/837 files...")
    from X12_837 import run as run_x12
    success = run_x12(x12_dir, x12_deid_dir)
    if success:
        print("\n✓ X12 837 de-identification completed successfully!")
    else:
        print("\n✗ X12 837 de-identification process failed!")
    return success


def main():
    run_Member()
    run_Claims()
    run_GuidingCare()
    run_Provider()
    run_X12_837()


if __name__ == "__main__":
    main()

