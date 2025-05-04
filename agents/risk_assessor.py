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

def get_patient_vitals(patient: Dict[str, Any]) -> Dict[str, str]:
    """Extract patient vitals from extensions."""
    vitals = {}
    for ext in patient.get("extension", []):
        if "blood-pressure" in ext.get("url", ""):
            vitals["blood_pressure"] = ext.get("valueString", "")
        elif "hba1c" in ext.get("url", ""):
            vitals["hba1c"] = ext.get("valueString", "")
        elif "cholesterol" in ext.get("url", ""):
            vitals["cholesterol"] = ext.get("valueString", "")
    return vitals

def get_patient_conditions(patient_data: Dict[str, Any], patient_id: str) -> List[Dict[str, Any]]:
    """Get all conditions for a specific patient."""
    conditions = []
    for entry in patient_data["entry"]:
        if entry["resource"]["resourceType"] == "Condition":
            subject = entry["resource"].get("subject", {})
            if subject.get("reference") == f"Patient/{patient_id}":
                conditions.append(entry["resource"])
    return conditions

def create_risk_assessor_agent() -> StateGraph:
    """Create a risk assessor agent that evaluates patient health risks."""
    
    def assess_risk(state: RiskState) -> RiskState:
        """Assess patient risk based on their data."""
        risk_assessment = {}
        
        for entry in state["patient_data"]["entry"]:
            if entry["resource"]["resourceType"] == "Patient":
                patient = entry["resource"]
                patient_id = patient["id"]
                patient_name = f"{patient['name'][0]['given'][0]} {patient['name'][0]['family']}"
                print(f"[DEBUG] Assessing risk for patient: {patient_name}")
                
                # Get patient's vitals
                vitals = get_patient_vitals(patient)
                
                # Get patient's conditions
                conditions = get_patient_conditions(state["patient_data"], patient_id)
                
                # Count severe conditions
                severe_conditions = sum(1 for c in conditions 
                                     if c.get("code", {}).get("coding", [{}])[0].get("severity") == "severe")
                
                # Count moderate conditions
                moderate_conditions = sum(1 for c in conditions 
                                       if c.get("code", {}).get("coding", [{}])[0].get("severity") == "moderate")
                
                # Evaluate vitals
                bp_systolic = int(vitals.get("blood_pressure", "0/0").split("/")[0])
                hba1c = float(vitals.get("hba1c", "0"))
                cholesterol = int(vitals.get("cholesterol", "0"))
                
                # Determine risk level based on conditions and vitals
                risk_level = "LOW"
                explanation = []
                recommended_actions = []
                
                if severe_conditions >= 2 or (severe_conditions == 1 and moderate_conditions >= 2):
                    risk_level = "HIGH"
                    explanation.append("Multiple severe conditions present")
                    recommended_actions.extend([
                        "Schedule immediate follow-up appointment",
                        "Review and adjust medications",
                        "Consider specialist consultation"
                    ])
                elif severe_conditions == 1 or moderate_conditions >= 2:
                    risk_level = "MEDIUM"
                    explanation.append("Significant health conditions requiring attention")
                    recommended_actions.extend([
                        "Schedule follow-up within 2 weeks",
                        "Review current medications",
                        "Implement preventive measures"
                    ])
                
                # Add vitals-based risk factors
                if bp_systolic >= 160:
                    risk_level = "HIGH" if risk_level == "MEDIUM" else risk_level
                    explanation.append("Severely elevated blood pressure")
                    recommended_actions.append("Urgent blood pressure management needed")
                elif bp_systolic >= 140:
                    risk_level = "MEDIUM" if risk_level == "LOW" else risk_level
                    explanation.append("Elevated blood pressure")
                    recommended_actions.append("Blood pressure monitoring recommended")
                
                if hba1c >= 9.0:
                    risk_level = "HIGH" if risk_level == "MEDIUM" else risk_level
                    explanation.append("Poorly controlled diabetes")
                    recommended_actions.append("Diabetes management review needed")
                elif hba1c >= 7.0:
                    risk_level = "MEDIUM" if risk_level == "LOW" else risk_level
                    explanation.append("Suboptimal diabetes control")
                    recommended_actions.append("Diabetes management adjustment recommended")
                
                if cholesterol >= 240:
                    risk_level = "MEDIUM" if risk_level == "LOW" else risk_level
                    explanation.append("Elevated cholesterol")
                    recommended_actions.append("Cholesterol management review recommended")
                
                risk_assessment[patient_name] = {
                    "risk_level": risk_level,
                    "explanation": " ".join(explanation),
                    "recommended_actions": recommended_actions
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