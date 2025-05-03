#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from typing import Dict, Any
import sys
from datetime import datetime

from agents.workflow import run_workflow, load_patient_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/workflow.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def ensure_directories():
    """Ensure all required directories exist."""
    directories = ['output', 'output/emails']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")

def run_pipeline() -> Dict[str, Any]:
    """Run the complete LangGraph pipeline."""
    try:
        # Ensure directories exist
        ensure_directories()
        
        # Load patient data
        logger.info("Loading patient data from data/patients.json")
        patient_data = load_patient_data()
        logger.info(f"Loaded data for {len(patient_data['entry'])} entries")
        
        # Run the workflow
        logger.info("Starting LangGraph workflow")
        start_time = datetime.now()
        result = run_workflow(patient_data)
        end_time = datetime.now()
        
        # Log completion
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Workflow completed in {duration:.2f} seconds")
        
        # Verify outputs
        verify_outputs()
        
        return result
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in patients.json: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during pipeline execution: {e}")
        raise

def verify_outputs():
    """Verify that all expected output files were created."""
    expected_files = [
        'output/summary.md',
        'output/risk_labels.json'
    ]
    
    # Check for email files
    email_files = list(Path('output/emails').glob('*.txt'))
    
    for file_path in expected_files:
        if not Path(file_path).exists():
            logger.error(f"Missing expected output file: {file_path}")
            raise FileNotFoundError(f"Missing output file: {file_path}")
        else:
            logger.info(f"Verified output file exists: {file_path}")
    
    if not email_files:
        logger.error("No email files were generated")
        raise FileNotFoundError("No email files found in output/emails/")
    else:
        logger.info(f"Generated {len(email_files)} email files")

def main():
    """Main entry point for the script."""
    try:
        logger.info("Starting HospitalGPT2 pipeline")
        result = run_pipeline()
        logger.info("Pipeline completed successfully")
        
        # Print summary of outputs
        print("\nPipeline completed successfully!")
        print("\nOutputs generated:")
        print("- /output/summary.md")
        print("- /output/risk_labels.json")
        print(f"- /output/emails/*.txt ({len(list(Path('output/emails').glob('*.txt')))} files)")
        print("\nCheck output/workflow.log for detailed execution log")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        print(f"\nError: Pipeline failed - {e}")
        print("Check output/workflow.log for details")
        sys.exit(1)

if __name__ == "__main__":
    main() 