from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END
from utils.query_helpers import FHIRQueryHelper, openrouter_chat

# Define the state type for our graph
class OutreachState(TypedDict):
    messages: List[Dict[str, Any]]
    patient_data: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    outreach_drafts: Dict[str, str]

def get_patient_details(patient_data: Dict[str, Any], patient_name: str) -> Dict[str, Any]:
    """Get detailed patient information including vitals and conditions."""
    patient_info = {}
    
    # Find the patient entry
    for entry in patient_data["entry"]:
        if entry["resource"]["resourceType"] == "Patient":
            name = f"{entry['resource']['name'][0]['given'][0]} {entry['resource']['name'][0]['family']}"
            if name == patient_name:
                patient_info["patient"] = entry["resource"]
                patient_info["vitals"] = {}
                
                # Get vitals from extensions
                for ext in entry["resource"].get("extension", []):
                    if "blood-pressure" in ext.get("url", ""):
                        patient_info["vitals"]["blood_pressure"] = ext.get("valueString", "")
                    elif "hba1c" in ext.get("url", ""):
                        patient_info["vitals"]["hba1c"] = ext.get("valueString", "")
                    elif "cholesterol" in ext.get("url", ""):
                        patient_info["vitals"]["cholesterol"] = ext.get("valueString", "")
                
                # Get conditions
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
    """Create an outreach agent that generates personalized emails."""
    
    def generate_outreach(state: OutreachState) -> Dict[str, Any]:
        outreach_drafts = {}
        
        for patient_name, assessment in state["risk_assessment"].items():
            print(f"[DEBUG] Generating outreach for {patient_name} with risk level {assessment['risk_level']}")
            
            # Get detailed patient information
            patient_info = get_patient_details(state["patient_data"], patient_name)
            
            # Generate outreach email using OpenRouter
            prompt = f"""Generate a personalized outreach email for {patient_name}:

Patient Details:
- Risk Level: {assessment['risk_level']}
- Assessment: {assessment['explanation']}
- Recommended Actions: {', '.join(assessment['recommended_actions'])}

Health Information:
- Blood Pressure: {patient_info.get('vitals', {}).get('blood_pressure', 'Not recorded')}
- HbA1c: {patient_info.get('vitals', {}).get('hba1c', 'Not recorded')}
- Cholesterol: {patient_info.get('vitals', {}).get('cholesterol', 'Not recorded')}
- Conditions: {', '.join(f"{c['name']} ({c['severity']})" for c in patient_info.get('conditions', []))}

Create a professional, empathetic email that:
1. Addresses their specific health concerns and risk level
2. References their actual conditions and vitals
3. Outlines the recommended actions in a clear, actionable way
4. Maintains a supportive and encouraging tone
5. Includes specific next steps and timeline for follow-up

Format the email with:
- A clear subject line
- Professional greeting
- Well-structured paragraphs
- Bullet points for actions
- Professional closing"""
            
            print(f"[DEBUG] Using openrouter_chat for {patient_name}")
            email = openrouter_chat([
                {"role": "user", "content": prompt}
            ])
            print(f"[DEBUG] openrouter_chat response for {patient_name}: {email}")
            outreach_drafts[patient_name] = email
        
        state["outreach_drafts"] = outreach_drafts
        return state
    
    # Create the graph
    workflow = StateGraph(OutreachState)
    
    # Add the outreach generation node
    workflow.add_node("generate", generate_outreach)
    
    # Set the entry point
    workflow.set_entry_point("generate")
    
    # Set the exit point
    workflow.add_edge("generate", END)
    
    # Compile the graph
    return workflow.compile()

if __name__ == "__main__":
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