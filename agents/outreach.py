from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END
from utils.query_helpers import FHIRQueryHelper, openrouter_chat

class OutreachState(TypedDict):
    """The current state of our patient outreach.
    
    This keeps track of:
    - Messages between agents
    - The patient data we're using
    - Risk assessments we've made
    - Email drafts we're creating
    """
    messages: List[Dict[str, Any]]
    patient_data: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    outreach_drafts: Dict[str, str]

def get_patient_details(patient_data: Dict[str, Any], patient_name: str) -> Dict[str, Any]:
    """Get all the important information about a patient.
    
    We collect:
    - Their basic information
    - Vital signs
    - Health conditions
    - Severity of each condition
    """
    patient_info = {}
    
    # Find this patient's record
    for entry in patient_data["entry"]:
        if entry["resource"]["resourceType"] == "Patient":
            name = f"{entry['resource']['name'][0]['given'][0]} {entry['resource']['name'][0]['family']}"
            if name == patient_name:
                patient_info["patient"] = entry["resource"]
                patient_info["vitals"] = {}
                
                # Get their vital signs
                for ext in entry["resource"].get("extension", []):
                    if "blood-pressure" in ext.get("url", ""):
                        patient_info["vitals"]["blood_pressure"] = ext.get("valueString", "")
                    elif "hba1c" in ext.get("url", ""):
                        patient_info["vitals"]["hba1c"] = ext.get("valueString", "")
                    elif "cholesterol" in ext.get("url", ""):
                        patient_info["vitals"]["cholesterol"] = ext.get("valueString", "")
                
                # Get their health conditions
                patient_info["conditions"] = []
                for cond_entry in patient_data["entry"]:
                    if cond_entry["resource"]["resourceType"] == "Condition":
                        subject = cond_entry["resource"].get("subject", {})
                        if subject.get("reference") == f"Patient/{entry['resource']['id']}":
                            condition = cond_entry["resource"]
                            severity = condition.get("code", {}).get("coding", [{}])[0].get("severity", "unknown")
                            display = condition.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
                            patient_info["conditions"].append({
                                "name": display,
                                "severity": severity
                            })
                break
    
    return patient_info

def create_outreach_agent() -> StateGraph:
    """Create an agent that writes personalized emails to patients.
    
    This agent:
    1. Looks at each patient's risk assessment
    2. Gathers their health information
    3. Writes a personalized email
    4. Explains their risk level
    5. Suggests next steps
    """
    
    def generate_outreach(state: OutreachState) -> Dict[str, Any]:
        """Create personalized emails for each patient.
        
        We write emails that:
        - Address their specific health concerns
        - Explain their risk level clearly
        - Suggest concrete next steps
        - Maintain a supportive tone
        """
        outreach_drafts = {}
        
        for patient_name, assessment in state["risk_assessment"].items():
            print(f"Writing email for {patient_name} (Risk Level: {assessment['risk_level']})")
            
            # Get all the patient's health information
            patient_info = get_patient_details(state["patient_data"], patient_name)
            
            # Create a personalized email
            prompt = f"""Please write a personalized email for {patient_name}:

Patient's Health Status:
- Risk Level: {assessment['risk_level']}
- Assessment: {assessment['explanation']}
- Recommended Actions: {', '.join(assessment['recommended_actions'])}

Health Information:
- Blood Pressure: {patient_info.get('vitals', {}).get('blood_pressure', 'Not recorded')}
- HbA1c: {patient_info.get('vitals', {}).get('hba1c', 'Not recorded')}
- Cholesterol: {patient_info.get('vitals', {}).get('cholesterol', 'Not recorded')}
- Health Conditions: {', '.join(f"{c['name']} ({c['severity']})" for c in patient_info.get('conditions', []))}

Please write an email that:
1. Addresses their specific health situation
2. Explains their risk level in clear terms
3. References their actual health data
4. Outlines clear next steps
5. Maintains a supportive and encouraging tone

Format the email with:
- A clear subject line
- Professional greeting
- Well-organized paragraphs
- Bullet points for actions
- Professional closing"""
            
            print(f"Generating email for {patient_name}...")
            email = openrouter_chat([
                {"role": "user", "content": prompt}
            ])
            outreach_drafts[patient_name] = email
        
        state["outreach_drafts"] = outreach_drafts
        return state
    
    # Set up our email writing workflow
    workflow = StateGraph(OutreachState)
    workflow.add_node("generate", generate_outreach)
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", END)
    return workflow.compile()

if __name__ == "__main__":
    # Example of how to generate patient emails
    import json
    with open("data/patients.json", "r") as f:
        patient_data = json.load(f)
    agent = create_outreach_agent()
    result = agent.invoke({
        "messages": [],
        "patient_data": patient_data,
        "risk_assessment": {
            "John Smith": {
                "risk_level": "HIGH",
                "explanation": "Patient has severe diabetes with multiple risk factors",
                "recommended_actions": ["Schedule follow-up appointment", "Review medication"]
            }
        },
        "outreach_drafts": {}
    })
    print(result["outreach_drafts"]) 