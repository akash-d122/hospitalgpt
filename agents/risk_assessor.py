from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END
from utils.query_helpers import FHIRQueryHelper, openrouter_chat

# Define risk levels
RISK_LEVELS = {
    "LOW": "Low risk - Regular monitoring recommended",
    "MEDIUM": "Medium risk - Increased monitoring and preventive measures recommended",
    "HIGH": "High risk - Immediate intervention recommended"
}

# Define the state type for our graph
class RiskState(TypedDict):
    messages: List[Dict[str, Any]]
    patient_data: Dict[str, Any]
    risk_assessment: Dict[str, Any]

def create_risk_assessor_agent() -> StateGraph:
    """Create a risk assessor agent that evaluates patient health risks."""
    
    def assess_risk(state: RiskState) -> RiskState:
        """Assess patient risk based on their data."""
        risk_assessment = {}
        
        for entry in state["patient_data"]["entry"]:
            if entry["resource"]["resourceType"] == "Patient":
                patient = entry["resource"]
                patient_name = f"{patient['name'][0]['given'][0]} {patient['name'][0]['family']}"
                print(f"[DEBUG] Assessing risk for patient: {patient_name}")
                
                # Get patient's conditions
                conditions = []
                for cond_entry in state["patient_data"]["entry"]:
                    if cond_entry["resource"]["resourceType"] == "Condition":
                        code = cond_entry["resource"].get("code", {})
                        condition_text = code.get("text") or (code.get("coding", [{}])[0].get("display", "Unknown"))
                        conditions.append(condition_text)
                print(f"[DEBUG] Using openrouter_chat for {patient_name} with conditions: {conditions}")
                
                # Generate risk assessment using OpenRouter
                prompt = f"""Assess the risk level for patient {patient_name}:
                Age: {patient.get('birthDate', 'N/A')}
                Conditions: {conditions}
                
                Provide a risk assessment with:
                1. Risk Level (HIGH/MEDIUM/LOW)
                2. Brief explanation
                3. Recommended actions"""
                
                assessment = openrouter_chat([
                    {"role": "user", "content": prompt}
                ])
                print(f"[DEBUG] openrouter_chat response for {patient_name}: {assessment}")
                
                # Parse the response to extract risk level
                risk_level = "MEDIUM"  # Default
                if "HIGH" in assessment.upper():
                    risk_level = "HIGH"
                elif "LOW" in assessment.upper():
                    risk_level = "LOW"
                
                risk_assessment[patient_name] = {
                    "risk_level": risk_level,
                    "explanation": assessment,
                    "recommended_actions": []
                }
        
        state["risk_assessment"] = risk_assessment
        return state
    
    # Create the graph
    workflow = StateGraph(RiskState)
    
    # Add the risk assessment node
    workflow.add_node("assess", assess_risk)
    
    # Set the entry point
    workflow.set_entry_point("assess")
    
    # Set the exit point
    workflow.add_edge("assess", END)
    
    # Compile the graph
    return workflow.compile()

if __name__ == "__main__":
    import json
    with open("data/patients.json", "r") as f:
        patient_data = json.load(f)
    agent = create_risk_assessor_agent()
    result = agent.invoke({
        "messages": [],
        "patient_data": patient_data,
        "risk_assessment": {}
    })
    print(result["risk_assessment"]) 