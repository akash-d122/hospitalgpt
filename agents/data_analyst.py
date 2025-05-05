from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END
from utils.query_helpers import FHIRQueryHelper, openrouter_chat

class AnalystState(TypedDict):
    """The current state of our data analysis.
    
    This keeps track of:
    - Messages between agents
    - The patient data we're analyzing
    - The summary we're building
    """
    messages: List[Dict[str, Any]]
    patient_data: Dict[str, Any]
    summary: str

def create_data_analyst_agent() -> StateGraph:
    """Create an agent that analyzes patient data and finds important patterns.
    
    This agent:
    1. Looks at all patient records
    2. Calculates key statistics
    3. Identifies important trends
    4. Creates a clear summary of findings
    """
    
    def analyze_patients(state: Dict[str, Any]) -> Dict[str, Any]:
        """Look through patient records and find important patterns.
        
        We analyze:
        - How many patients we have
        - Their age distribution
        - Common health conditions
        - Any notable patterns in the data
        """
        # Get all patient records
        patients = [entry["resource"] for entry in state["patient_data"]["entry"] 
                   if entry["resource"]["resourceType"] == "Patient"]
        
        # Calculate basic statistics
        total_patients = len(patients)
        age_distribution = {}
        conditions = {}
        
        print(f"Analyzing {total_patients} patient records...")
        
        for patient in patients:
            # Figure out how old each patient is
            birth_date = patient.get("birthDate", "")
            if birth_date:
                age = 2024 - int(birth_date.split("-")[0])  # Simple age calculation
                age_range = f"{(age // 10) * 10}-{(age // 10) * 10 + 9}"
                age_distribution[age_range] = age_distribution.get(age_range, 0) + 1
            
            # Track what conditions patients have
            for entry in state["patient_data"]["entry"]:
                if entry["resource"]["resourceType"] == "Condition":
                    code = entry["resource"].get("code", {})
                    condition = code.get("text") or (code.get("coding", [{}])[0].get("display", "Unknown"))
                    conditions[condition] = conditions.get(condition, 0) + 1
        
        # Create a summary of what we found
        prompt = f"""Please analyze this patient data and create a clear summary:

        Total Patients: {total_patients}
        Age Distribution: {age_distribution}
        Common Conditions: {conditions}
        
        Focus on:
        - Key patterns in the data
        - Important health trends
        - Any notable patient groups
        - Areas that might need attention"""
        
        summary = openrouter_chat([
            {"role": "user", "content": prompt}
        ])
        
        state["summary"] = summary
        return state
    
    # Set up our analysis workflow
    workflow = StateGraph(AnalystState)
    workflow.add_node("analyze", analyze_patients)
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", END)
    return workflow.compile()

if __name__ == "__main__":
    # Example of how to run the analysis
    import json
    with open("data/patients.json", "r") as f:
        patient_data = json.load(f)
    agent = create_data_analyst_agent()
    result = agent.invoke({
        "messages": [],
        "patient_data": patient_data,
        "summary": ""
    })
    print(result["summary"]) 