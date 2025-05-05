from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END
import os
from dotenv import load_dotenv
import json
from pathlib import Path
import re
import time
from urllib3.exceptions import MaxRetryError, ConnectTimeoutError

# Import our specialized analysis agents
from agents.data_analyst import create_data_analyst_agent
from agents.risk_assessor import create_risk_assessor_agent
from agents.outreach import create_outreach_agent

# Load environment variables (like API keys)
load_dotenv()

class WorkflowState(TypedDict):
    """The state of our analysis workflow at any point in time.
    
    This keeps track of:
    - Messages between agents
    - Patient data being analyzed
    - The analysis summary
    - Risk assessment results
    - Draft emails for patients
    """
    messages: List[Dict[str, Any]]
    patient_data: Dict[str, Any]
    summary: str
    risk_assessment: Dict[str, Any]
    outreach_drafts: Dict[str, str]

def ensure_output_dirs():
    """Create the folders where we'll save our analysis results."""
    Path("output").mkdir(exist_ok=True)
    Path("output/emails").mkdir(exist_ok=True)

def sanitize_filename(name: str) -> str:
    """Make a string safe to use as a filename.
    
    Removes any characters that could cause problems in filenames
    and replaces spaces with underscores.
    """
    return re.sub(r'[<>:"/\\|?*]', '', name).replace(' ', '_')

def load_patient_data() -> Dict[str, Any]:
    """Read the patient records from our JSON file."""
    with open("data/patients.json", "r", encoding='utf-8') as f:
        return json.load(f)

def retry_with_backoff(func, max_retries=3, initial_delay=1):
    """Try to run a function multiple times if it fails.
    
    This is useful when dealing with external services that might
    be temporarily unavailable. Each retry waits longer than the last.
    """
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return func()
        except (MaxRetryError, ConnectTimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)
            delay *= 2  # Wait longer each time
            print(f"Retry attempt {attempt + 1} after {delay} seconds...")

def create_workflow() -> StateGraph:
    """Set up our analysis workflow.
    
    This creates a graph where:
    1. The data analyst looks at patient records
    2. The risk assessor evaluates potential issues
    3. The outreach agent drafts emails for patients
    
    Each step feeds into the next automatically.
    """
    # Start with an empty workflow
    workflow = StateGraph(WorkflowState)
    
    # Add our analysis steps
    workflow.add_node("analyze", create_data_analyst_agent())
    workflow.add_node("assess", create_risk_assessor_agent())
    workflow.add_node("outreach", create_outreach_agent())
    
    # Connect the steps in order
    workflow.add_edge("analyze", "assess")
    workflow.add_edge("assess", "outreach")
    workflow.add_edge("outreach", END)
    
    # Start with the analysis step
    workflow.set_entry_point("analyze")
    
    return workflow.compile()

def run_workflow(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run the complete analysis process.
    
    This function:
    1. Sets up the workflow
    2. Runs it with the patient data
    3. Saves all the results
    4. Handles any errors that come up
    """
    try:
        # Get our workflow ready
        workflow = create_workflow()
        
        # Start with empty results
        initial_state = {
            "messages": [],
            "patient_data": patient_data,
            "summary": "",
            "risk_assessment": {},
            "outreach_drafts": {}
        }
        
        # Try to run the workflow, with retries if needed
        def run_workflow_with_retry():
            try:
                return workflow.invoke(initial_state)
            except (MaxRetryError, ConnectTimeoutError) as e:
                print(f"Had trouble connecting to the analysis service: {str(e)}")
                # Return what we have so far
                return initial_state
        
        result = retry_with_backoff(run_workflow_with_retry)
        
        # Save everything we found
        save_outputs(result)
        
        return result
    except Exception as e:
        print(f"Something went wrong during the analysis: {str(e)}")
        # Try to save what we have, even if it's incomplete
        if 'result' in locals():
            save_outputs(result)
        raise

def save_outputs(state: WorkflowState):
    """Save all our analysis results to files.
    
    We create:
    - A summary of what we found
    - Risk assessment results
    - Personalized email drafts for each patient
    """
    # Save the analysis summary
    with open("output/summary.md", "w", encoding='utf-8') as f:
        f.write("# Patient Analysis Summary\n\n")
        f.write(state["summary"] if state["summary"] else "Couldn't generate summary due to connection issues.")
    
    # Save the risk assessments
    with open("output/risk_labels.json", "w", encoding='utf-8') as f:
        json.dump(state["risk_assessment"], f, indent=2)
    
    # Save email drafts for each patient
    Path("output/emails").mkdir(exist_ok=True)
    for patient_name, draft in state["outreach_drafts"].items():
        filename = sanitize_filename(patient_name)
        with open(f"output/emails/{filename}.txt", "w", encoding='utf-8') as f:
            f.write(draft if draft else "Couldn't generate email due to connection issues. Please check the analysis service.")

if __name__ == "__main__":
    # Example of how to run the analysis
    patient_data = load_patient_data()
    result = run_workflow(patient_data)
    print("Analysis completed successfully!") 