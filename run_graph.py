#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from typing import Dict, Any
import sys
from datetime import datetime
import glob
import os

from agents.workflow import run_workflow, load_patient_data

# Set up logging to both file and console
# This helps us track what's happening during execution
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/workflow.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def ensure_directories():
    """Create the necessary folders for storing our outputs.
    
    We need these directories to store:
    - The main output folder for all results
    - A subfolder for patient emails
    """
    directories = ['output', 'output/emails']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"Created directory: {directory}")

def clear_old_emails():
    """Remove any existing email files before starting a new run.
    
    This prevents confusion between old and new results.
    """
    for f in glob.glob('output/emails/*.txt'):
        os.remove(f)

def run_pipeline() -> Dict[str, Any]:
    """Run the complete analysis pipeline from start to finish.
    
    This function:
    1. Sets up the environment
    2. Loads patient data
    3. Runs the analysis workflow
    4. Verifies the outputs
    
    Returns:
        Dict[str, Any]: The final results of the analysis
    """
    try:
        # Get everything ready
        ensure_directories()
        clear_old_emails()
        
        # Load and process patient data
        logger.info("Loading patient records from data/patients.json")
        patient_data = load_patient_data()
        logger.info(f"Found {len(patient_data['entry'])} patient records to analyze")
        
        # Run the main analysis
        logger.info("Starting patient analysis workflow")
        start_time = datetime.now()
        result = run_workflow(patient_data)
        end_time = datetime.now()
        
        # Show how long it took
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Analysis completed in {duration:.2f} seconds")
        
        # Make sure we got all the expected results
        verify_outputs()
        
        return result
        
    except FileNotFoundError as e:
        logger.error(f"Couldn't find a required file: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Problem reading the patient data file: {e}")
        raise
    except Exception as e:
        logger.error(f"Something went wrong during the analysis: {e}")
        raise

def verify_outputs():
    """Check that we generated all the expected output files.
    
    We expect:
    - A summary markdown file
    - A risk assessment JSON file
    - At least one email draft for patients
    """
    expected_files = [
        'output/summary.md',
        'output/risk_labels.json'
    ]
    
    # Look for generated email files
    email_files = list(Path('output/emails').glob('*.txt'))
    
    for file_path in expected_files:
        if not Path(file_path).exists():
            logger.error(f"Missing an important output file: {file_path}")
            raise FileNotFoundError(f"Missing output file: {file_path}")
        else:
            logger.info(f"Found output file: {file_path}")
    
    if not email_files:
        logger.error("No email drafts were created")
        raise FileNotFoundError("No email files found in output/emails/")
    else:
        logger.info(f"Created {len(email_files)} email drafts")

def main():
    """The main entry point for running the analysis.
    
    This function:
    1. Starts the pipeline
    2. Shows a summary of what was created
    3. Handles any errors that occur
    """
    try:
        logger.info("Starting HospitalGPT2 analysis pipeline")
        result = run_pipeline()
        logger.info("Pipeline finished successfully")
        
        # Show what we created
        print("\nAnalysis completed successfully!")
        print("\nHere's what we generated:")
        print("- /output/summary.md (Patient analysis summary)")
        print("- /output/risk_labels.json (Risk assessments)")
        print(f"- /output/emails/*.txt ({len(list(Path('output/emails').glob('*.txt')))} email drafts)")
        print("\nFor more details, check output/workflow.log")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        print(f"\nError: The analysis couldn't be completed - {e}")
        print("Check output/workflow.log for more information")
        sys.exit(1)

if __name__ == "__main__":
    main() 