from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END
from utils.query_helpers import FHIRQueryHelper, openrouter_chat

class AnalystState(TypedDict):
    messages: List[Dict[str, Any]]
    patient_data: Dict[str, Any]
    summary: str

def create_data_analyst_agent() -> StateGraph:
    """Create a data analyst agent that summarizes patient data."""
    
    def analyze_patients(state: Dict[str, Any]) -> Dict[str, Any]:
        # Extract patient information
        patients = [entry["resource"] for entry in state["patient_data"]["entry"] 
                   if entry["resource"]["resourceType"] == "Patient"]
        
        # Calculate statistics
        total_patients = len(patients)
        age_distribution = {}
        conditions = {}
        print("[DEBUG] Using openrouter_chat in data_analyst agent.")
        print(f"[DEBUG] Number of patients: {total_patients}")
        for patient in patients:
            # Age calculation
            birth_date = patient.get("birthDate", "")
            if birth_date:
                age = 2024 - int(birth_date.split("-")[0])  # Simple age calculation
                age_range = f"{(age // 10) * 10}-{(age // 10) * 10 + 9}"
                age_distribution[age_range] = age_distribution.get(age_range, 0) + 1
            
            # Condition tracking
            for entry in state["patient_data"]["entry"]:
                if entry["resource"]["resourceType"] == "Condition":
                    code = entry["resource"].get("code", {})
                    condition = code.get("text") or (code.get("coding", [{}])[0].get("display", "Unknown"))
                    conditions[condition] = conditions.get(condition, 0) + 1
        
        # Generate summary using OpenRouter
        prompt = f"""Analyze the following patient data and provide a concise summary:
        Total Patients: {total_patients}
        Age Distribution: {age_distribution}
        Conditions: {conditions}
        
        Please provide a brief summary focusing on key patterns and insights."""
        
        summary = openrouter_chat([
            {"role": "user", "content": prompt}
        ])
        
        state["summary"] = summary
        return state
    
    workflow = StateGraph(AnalystState)
    workflow.add_node("analyze", analyze_patients)
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", END)
    return workflow.compile()

if __name__ == "__main__":
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