from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END
from utils.query_helpers import FHIRQueryHelper, openrouter_chat

# Define what each risk level means for patients
RISK_LEVELS = {
    "LOW": "Low risk - Regular monitoring recommended",
    "MEDIUM": "Medium risk - Increased monitoring and preventive measures recommended",
    "HIGH": "High risk - Immediate intervention recommended"
}

class RiskState(TypedDict):
    """The current state of our risk assessment.
    
    This keeps track of:
    - Messages between agents
    - The patient data we're analyzing
    - The risk assessments we're building
    """
    messages: List[Dict[str, Any]]
    patient_data: Dict[str, Any]
    risk_assessment: Dict[str, Any]

def get_patient_vitals(patient: Dict[str, Any]) -> Dict[str, str]:
    """Get a patient's vital signs from their record.
    
    We look for:
    - Blood pressure readings
    - HbA1c levels (for diabetes)
    - Cholesterol levels
    """
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
    """Find all health conditions for a specific patient.
    
    This helps us understand:
    - What conditions they have
    - How severe each condition is
    - How many conditions they're dealing with
    """
    conditions = []
    for entry in patient_data["entry"]:
        if entry["resource"]["resourceType"] == "Condition":
            subject = entry["resource"].get("subject", {})
            if subject.get("reference") == f"Patient/{patient_id}":
                conditions.append(entry["resource"])
    return conditions

def create_risk_assessor_agent() -> StateGraph:
    """Create an agent that evaluates how at-risk each patient is.
    
    This agent:
    1. Looks at each patient's health data
    2. Checks their vital signs
    3. Reviews their conditions
    4. Determines their risk level
    5. Suggests what to do next
    """
    
    def assess_risk(state: RiskState) -> RiskState:
        """Evaluate how at-risk each patient is based on their health data.
        
        We consider:
        - How many serious conditions they have
        - Their vital signs
        - Any concerning patterns
        - What kind of follow-up they need
        """
        risk_assessment = {}
        
        for entry in state["patient_data"]["entry"]:
            if entry["resource"]["resourceType"] == "Patient":
                patient = entry["resource"]
                patient_id = patient["id"]
                patient_name = f"{patient['name'][0]['given'][0]} {patient['name'][0]['family']}"
                print(f"Assessing risk for {patient_name}...")
                
                # Get the patient's vital signs
                vitals = get_patient_vitals(patient)
                
                # Find all their health conditions
                conditions = get_patient_conditions(state["patient_data"], patient_id)
                
                # Count how many serious conditions they have
                severe_conditions = sum(1 for c in conditions 
                                     if c.get("code", {}).get("coding", [{}])[0].get("severity") == "severe")
                
                # Count moderate conditions too
                moderate_conditions = sum(1 for c in conditions 
                                       if c.get("code", {}).get("coding", [{}])[0].get("severity") == "moderate")
                
                # Check their vital signs
                bp_systolic = int(vitals.get("blood_pressure", "0/0").split("/")[0])
                hba1c = float(vitals.get("hba1c", "0"))
                cholesterol = int(vitals.get("cholesterol", "0"))
                
                # Start with low risk and adjust based on what we find
                risk_level = "LOW"
                explanation = []
                recommended_actions = []
                
                # Check for multiple serious conditions
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
                
                # Check blood pressure
                if bp_systolic >= 160:
                    risk_level = "HIGH" if risk_level == "MEDIUM" else risk_level
                    explanation.append("Severely elevated blood pressure")
                    recommended_actions.append("Urgent blood pressure management needed")
                elif bp_systolic >= 140:
                    risk_level = "MEDIUM" if risk_level == "LOW" else risk_level
                    explanation.append("Elevated blood pressure")
                    recommended_actions.append("Blood pressure monitoring recommended")
                
                # Check diabetes control
                if hba1c >= 9.0:
                    risk_level = "HIGH" if risk_level == "MEDIUM" else risk_level
                    explanation.append("Poorly controlled diabetes")
                    recommended_actions.append("Diabetes management review needed")
                elif hba1c >= 7.0:
                    risk_level = "MEDIUM" if risk_level == "LOW" else risk_level
                    explanation.append("Suboptimal diabetes control")
                    recommended_actions.append("Diabetes management adjustment recommended")
                
                # Check cholesterol
                if cholesterol >= 240:
                    risk_level = "MEDIUM" if risk_level == "LOW" else risk_level
                    explanation.append("Elevated cholesterol")
                    recommended_actions.append("Cholesterol management review recommended")
                
                # Save our assessment
                risk_assessment[patient_name] = {
                    "risk_level": risk_level,
                    "explanation": " ".join(explanation),
                    "recommended_actions": recommended_actions
                }
        
        state["risk_assessment"] = risk_assessment
        return state
    
    # Set up our risk assessment workflow
    workflow = StateGraph(RiskState)
    workflow.add_node("assess", assess_risk)
    workflow.set_entry_point("assess")
    workflow.add_edge("assess", END)
    return workflow.compile()

if __name__ == "__main__":
    # Example of how to run the risk assessment
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