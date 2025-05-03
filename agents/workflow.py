from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END
import os
from dotenv import load_dotenv
import json
from pathlib import Path
import re

# Import our agents
from agents.data_analyst import create_data_analyst_agent
from agents.risk_assessor import create_risk_assessor_agent
from agents.outreach import create_outreach_agent

load_dotenv()

# Define the state type for our graph
class WorkflowState(TypedDict):
    messages: List[Dict[str, Any]]
    patient_data: Dict[str, Any]
    summary: str
    risk_assessment: Dict[str, Any]
    outreach_drafts: Dict[str, str]

def ensure_output_dirs():
    """Create output directories if they don't exist."""
    Path("output").mkdir(exist_ok=True)
    Path("output/emails").mkdir(exist_ok=True)

def sanitize_filename(name: str) -> str:
    """Convert a string to a valid filename."""
    # Remove invalid characters and replace spaces with underscores
    return re.sub(r'[<>:"/\\|?*]', '', name).replace(' ', '_')

def load_patient_data() -> Dict[str, Any]:
    """Load patient data from the JSON file."""
    with open("data/patients.json", "r") as f:
        return json.load(f)

def create_workflow() -> StateGraph:
    """Create the LangGraph workflow."""
    # Initialize the graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("analyze", create_data_analyst_agent())
    workflow.add_node("assess", create_risk_assessor_agent())
    workflow.add_node("outreach", create_outreach_agent())
    
    # Define edges
    workflow.add_edge("analyze", "assess")
    workflow.add_edge("assess", "outreach")
    workflow.add_edge("outreach", END)
    
    # Set entry point
    workflow.set_entry_point("analyze")
    
    return workflow.compile()

def run_workflow(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run the complete workflow."""
    # Create workflow
    workflow = create_workflow()
    
    # Initialize state
    initial_state = {
        "messages": [],
        "patient_data": patient_data,
        "summary": "",
        "risk_assessment": {},
        "outreach_drafts": {}
    }
    
    # Run workflow
    result = workflow.invoke(initial_state)
    
    # Save outputs
    save_outputs(result)
    
    return result

def save_outputs(state: WorkflowState):
    """Save workflow outputs to files."""
    # Save summary
    with open("output/summary.md", "w") as f:
        f.write("# Patient Analysis Summary\n\n")
        f.write(state["summary"])
    
    # Save risk assessment
    with open("output/risk_labels.json", "w") as f:
        json.dump(state["risk_assessment"], f, indent=2)
    
    # Save outreach drafts
    Path("output/emails").mkdir(exist_ok=True)
    for patient_name, draft in state["outreach_drafts"].items():
        filename = sanitize_filename(patient_name)
        with open(f"output/emails/{filename}.txt", "w") as f:
            f.write(draft)

if __name__ == "__main__":
    # Example usage
    patient_data = load_patient_data()
    result = run_workflow(patient_data)
    print("Workflow completed successfully!") 